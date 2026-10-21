using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.ExceptionServices;
using System.Security;
using System.Threading;
using RAMDATAACCESSLib;

// Floor loads for a RAM Frame run, through RAM DataAccess.
//
//   RamLateralLoads.exe inspect MODEL.rss [--vertices]
//   RamLateralLoads.exe apply SOURCE.rss OUTPUT.rss SPEC.tsv [--replace-output]
//
// apply copies SOURCE to OUTPUT and edits only OUTPUT. RAM must not have
// OUTPUT open. SPEC rows (tab separated, # comments), in office units
// (psf for surface loads, k/ft for line loads):
//
//   surface  LABEL  dl=  ll=  lltype=reducible|unreducible|storage|roof  mass=  partition=
//   line     LABEL  dl=  ll=  mass=
//   isolate  STORY  NEW_LABEL_FOR_THAT_STORY  LABEL_FOR_THE_OTHER_STORIES
//   area     FLOOR_TYPE  SURFACE_LABEL        (the largest slab perimeter)
//   perimeter FLOOR_TYPE LINE_LABEL [skip_x=FT] [skip_y=FT]
//            (every edge of the largest slab perimeter, except edges lying
//             on a skipped line, e.g. an expansion joint)
//
// Only the largest slab perimeter is loaded: a small perimeter inside it is
// an opening drawn as a slab edge loop, not floor.
internal static class RamLateralLoads
{
    private const double PsfToKsi = 1.0 / 144000.0;
    private const double KlfToKpi = 1.0 / 12.0;
    private const double MinEdgeInches = 1.0;

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            if ((args.Length == 2 || args.Length == 3) && args[0] == "inspect")
            {
                var vertices = args.Length == 3 && args[2] == "--vertices";
                if (args.Length == 3 && !vertices)
                {
                    return Usage();
                }
                return Inspect(Path.GetFullPath(args[1]), vertices);
            }
            if ((args.Length == 4 || args.Length == 5) && args[0] == "apply")
            {
                var replace = args.Length == 5 && args[4] == "--replace-output";
                if (args.Length == 5 && !replace)
                {
                    return Usage();
                }
                return Apply(
                    Path.GetFullPath(args[1]),
                    Path.GetFullPath(args[2]),
                    Path.GetFullPath(args[3]),
                    replace);
            }
            return Usage();
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.ToString());
            return 1;
        }
    }

    private static int Usage()
    {
        Console.Error.WriteLine(
            "Usage: RamLateralLoads.exe inspect MODEL.rss\n" +
            "       RamLateralLoads.exe apply SOURCE.rss OUTPUT.rss SPEC.tsv [--replace-output]");
        return 2;
    }

    private static int Inspect(string model, bool vertices)
    {
        if (!File.Exists(model))
        {
            Console.Error.WriteLine("Model not found: " + model);
            return 2;
        }
        var session = Open(model, "AgenticRAM_LateralLoads_ReadOnly");
        try
        {
            Report(session.Model);
            if (vertices)
            {
                DumpVertices(session.Model);
            }
        }
        finally
        {
            Close(session.Database);
        }
        return 0;
    }

    private static int Apply(string source, string output, string specPath, bool replace)
    {
        if (!File.Exists(source))
        {
            Console.Error.WriteLine("Source not found: " + source);
            return 2;
        }
        if (string.Equals(source, output, StringComparison.OrdinalIgnoreCase))
        {
            Console.Error.WriteLine("OUTPUT must differ from SOURCE; the source model is never edited.");
            return 2;
        }
        if (File.Exists(output) && !replace)
        {
            Console.Error.WriteLine("Output exists (pass --replace-output to overwrite it): " + output);
            return 2;
        }
        var spec = ReadSpec(specPath);
        File.Copy(source, output, true);

        var session = Open(output, "AgenticRAM_LateralLoads");
        try
        {
            var model = session.Model;
            var surfaceUids = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            var lineUids = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

            foreach (var row in spec)
            {
                switch (row[0])
                {
                    case "surface":
                        surfaceUids[row[1]] = AddSurfaceProperty(model, row);
                        break;
                    case "line":
                        lineUids[row[1]] = AddLineProperty(model, row);
                        break;
                    case "isolate":
                        IsolateStory(model, row[1], row[2], row[3]);
                        break;
                    case "area":
                        PlaceArea(model, row[1], Lookup(surfaceUids, row[2], "surface"), row[2]);
                        break;
                    case "perimeter":
                        PlacePerimeter(model, row[1], Lookup(lineUids, row[2], "line"), row[2], Options(row, 3));
                        break;
                    default:
                        throw new InvalidDataException("Unknown spec row: " + row[0]);
                }
            }

            if (!Save(session.Database))
            {
                return 3;
            }
            Console.WriteLine("SAVED\t" + output);
            Report(model);
        }
        finally
        {
            Close(session.Database);
        }
        return 0;
    }

    private sealed class Session
    {
        public IDBIO1 Database;
        public IModel Model;
    }

    private static Session Open(string model, string user)
    {
        var dataAccess = new RamDataAccess1Class();
        var database = (IDBIO1)dataAccess.GetDispInterfacePointerByEnum(EINTERFACES.IDBIO1_INT);
        var status = database.LoadDataBase2(model, user);
        if (status != 0)
        {
            throw new InvalidOperationException("LoadDataBase2 returned " + status + " for " + model);
        }
        return new Session
        {
            Database = database,
            Model = (IModel)dataAccess.GetDispInterfacePointerByEnum(EINTERFACES.IModel_INT),
        };
    }

    // SaveDatabase raised an access violation from a standalone process on
    // RAM SS 26.00.00.222. Catch it and report RAM's own last error.
    [HandleProcessCorruptedStateExceptions, SecurityCritical]
    private static bool Save(IDBIO1 database)
    {
        try
        {
            database.SaveDatabase();
            return true;
        }
        catch (Exception ex)
        {
            Console.WriteLine("SAVE_FAILED\t" + ex.GetType().Name + "\t" + ex.Message);
            try
            {
                string function = "", message = "";
                int code = 0;
                database.GetLastError(ref function, ref message, ref code);
                Console.WriteLine("RAM_LAST_ERROR\t{0}\t{1}\t{2}", code, function, message);
            }
            catch (Exception inner)
            {
                Console.WriteLine("GET_LAST_ERROR_FAILED\t" + inner.GetType().Name);
            }
            Console.Out.Flush();
            return false;
        }
    }

    // CloseDatabase raised an access violation after a clean read on RAM SS
    // 2025 (as in RamSlabGeometryExporter); close on a background thread so
    // the saved files and the report are not lost with it.
    private static void Close(IDBIO1 database)
    {
        Console.Out.Flush();
        var closer = new Thread(delegate()
        {
            try
            {
                database.CloseDatabase();
            }
            catch
            {
            }
        });
        closer.IsBackground = true;
        closer.Start();
        closer.Join(5000);
    }

    private static void DumpVertices(IModel model)
    {
        var types = model.GetFloorTypes();
        for (var i = 0; i < types.GetCount(); i++)
        {
            var type = types.GetAt(i);
            var perimeters = type.GetSlabPerimeters();
            for (var p = 0; p < perimeters.GetCount(); p++)
            {
                var polygon = Vertices(perimeters.GetAt(p));
                for (var v = 0; v < polygon.Count; v++)
                {
                    Console.WriteLine(
                        string.Format(CultureInfo.InvariantCulture, "VERTEX	{0}	{1}	{2}	{3:F2}	{4:F2}",
                        type.strLabel, p, v, polygon[v][0] / 12.0, polygon[v][1] / 12.0));
                }
            }
        }
    }

    private static List<string[]> ReadSpec(string path)
    {
        var rows = new List<string[]>();
        foreach (var raw in File.ReadAllLines(path))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith("#"))
            {
                continue;
            }
            rows.Add(line.Split('\t'));
        }
        return rows;
    }

    private static Dictionary<string, string> Options(string[] row, int start)
    {
        var options = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (var i = start; i < row.Length; i++)
        {
            var parts = row[i].Split(new[] { '=' }, 2);
            if (parts.Length != 2)
            {
                throw new InvalidDataException("Expected key=value: " + row[i]);
            }
            options[parts[0].Trim()] = parts[1].Trim();
        }
        return options;
    }

    private static double Number(Dictionary<string, string> options, string key)
    {
        string text;
        return options.TryGetValue(key, out text)
            ? double.Parse(text, CultureInfo.InvariantCulture)
            : 0.0;
    }

    private static ELoadCaseType LiveType(string name)
    {
        switch ((name ?? "reducible").ToLowerInvariant())
        {
            case "reducible": return ELoadCaseType.LiveReducibleLCa;
            case "unreducible": return ELoadCaseType.LiveUnReducibleLCa;
            case "storage": return ELoadCaseType.LiveStorageLCa;
            case "roof": return ELoadCaseType.LiveRoofLCa;
            default: throw new InvalidDataException("Unknown live load type: " + name);
        }
    }

    private static int AddSurfaceProperty(IModel model, string[] row)
    {
        var options = Options(row, 2);
        var sets = model.GetSurfaceLoadPropertySets();
        for (var i = 0; i < sets.GetCount(); i++)
        {
            if (string.Equals(sets.GetAt(i).strLabel, row[1], StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException("Surface load property exists: " + row[1]);
            }
        }
        var property = sets.Add(row[1]);
        property.dDeadLoad = Number(options, "dl") * PsfToKsi;
        property.dLiveLoad = Number(options, "ll") * PsfToKsi;
        property.dMassDeadLoad = Number(options, "mass") * PsfToKsi;
        property.dPartitionLoad = Number(options, "partition") * PsfToKsi;
        string liveType;
        options.TryGetValue("lltype", out liveType);
        property.eLiveLoadType = LiveType(liveType);
        Console.WriteLine("SURFACE_PROPERTY\t{0}\tUID {1}", property.strLabel, property.lUID);
        return property.lUID;
    }

    private static int AddLineProperty(IModel model, string[] row)
    {
        var options = Options(row, 2);
        var sets = model.GetLineLoadPropertySets();
        for (var i = 0; i < sets.GetCount(); i++)
        {
            if (string.Equals(sets.GetAt(i).strLabel, row[1], StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException("Line load property exists: " + row[1]);
            }
        }
        var property = sets.Add(row[1]);
        property.dDeadLoad = Number(options, "dl") * KlfToKpi;
        property.dLiveLoad = Number(options, "ll") * KlfToKpi;
        property.dMassDeadLoad = Number(options, "mass") * KlfToKpi;
        string liveType;
        options.TryGetValue("lltype", out liveType);
        property.eLiveLoadType = LiveType(liveType);
        Console.WriteLine("LINE_PROPERTY\t{0}\tUID {1}", property.strLabel, property.lUID);
        return property.lUID;
    }

    private static int Lookup(Dictionary<string, int> uids, string label, string kind)
    {
        int uid;
        if (!uids.TryGetValue(label, out uid))
        {
            throw new InvalidDataException("No " + kind + " property defined above for: " + label);
        }
        return uid;
    }

    private static IStory FindStory(IModel model, string label)
    {
        var stories = model.GetStories();
        for (var i = 0; i < stories.GetCount(); i++)
        {
            var story = stories.GetAt(i);
            if (string.Equals(story.strLabel, label, StringComparison.OrdinalIgnoreCase))
            {
                return story;
            }
        }
        throw new InvalidDataException("Story not found: " + label);
    }

    private static IFloorType FindFloorType(IModel model, string label)
    {
        var types = model.GetFloorTypes();
        for (var i = 0; i < types.GetCount(); i++)
        {
            var type = types.GetAt(i);
            if (string.Equals(type.strLabel, label, StringComparison.OrdinalIgnoreCase))
            {
                return type;
            }
        }
        throw new InvalidDataException("Floor type not found: " + label);
    }

    // The isolated story keeps the original floor type; RAM gives the other
    // stories that shared it a copy. Both are then relabelled.
    private static void IsolateStory(IModel model, string storyLabel, string isolatedLabel, string othersLabel)
    {
        var story = FindStory(model, storyLabel);
        var sharedUid = story.GetFloorType().lUID;
        var before = new HashSet<int>();
        var types = model.GetFloorTypes();
        for (var i = 0; i < types.GetCount(); i++)
        {
            before.Add(types.GetAt(i).lUID);
        }

        story.IsolateFloorType();

        IFloorType copy = null;
        types = model.GetFloorTypes();
        for (var i = 0; i < types.GetCount(); i++)
        {
            if (!before.Contains(types.GetAt(i).lUID))
            {
                copy = types.GetAt(i);
            }
        }
        if (copy == null)
        {
            throw new InvalidOperationException("IsolateFloorType made no new floor type for " + storyLabel);
        }

        var isolated = FindStory(model, storyLabel).GetFloorType();
        var others = isolated.lUID == sharedUid ? copy : model.GetFloorType(sharedUid);
        isolated.strLabel = isolatedLabel;
        others.strLabel = othersLabel;
        Console.WriteLine(
            "ISOLATED\t{0}\t{1} (UID {2})\tothers {3} (UID {4})",
            storyLabel, isolated.strLabel, isolated.lUID, others.strLabel, others.lUID);
    }

    private static List<double[]> Vertices(ISlabPerimeter perimeter)
    {
        var points = new List<double[]>();
        var vertices = perimeter.GetPerimeterVertices();
        for (var i = 0; i < vertices.GetCount(); i++)
        {
            var coordinate = new SCoordinate();
            vertices.GetAt(i).GetCoordinate(ref coordinate);
            points.Add(new[] { coordinate.dXLoc, coordinate.dYLoc });
        }
        return points;
    }

    private static List<double[]> LargestPerimeter(IFloorType floor, string floorLabel)
    {
        var perimeters = floor.GetSlabPerimeters();
        List<double[]> largest = null;
        for (var p = 0; p < perimeters.GetCount(); p++)
        {
            var polygon = Vertices(perimeters.GetAt(p));
            if (largest == null || Math.Abs(Area(polygon)) > Math.Abs(Area(largest)))
            {
                largest = polygon;
            }
        }
        if (largest == null)
        {
            throw new InvalidOperationException("No slab perimeter on " + floorLabel);
        }
        if (perimeters.GetCount() > 1)
        {
            Console.WriteLine("NOTE	{0}	{1} slab perimeters; loading only the largest", floorLabel, perimeters.GetCount());
        }
        return largest;
    }

    private static void PlaceArea(IModel model, string floorLabel, int propertyUid, string propertyLabel)
    {
        var floor = FindFloorType(model, floorLabel);
        var polygon = LargestPerimeter(floor, floorLabel);
        var set = floor.GetSurfaceLoadSets2().Add(propertyUid, polygon.Count);
        var points = set.GetPoints();
        if (points.GetCount() == polygon.Count)
        {
            for (var i = 0; i < polygon.Count; i++)
            {
                points.GetAt(i).SetCoordinate2(polygon[i][0], polygon[i][1], 0.0);
            }
        }
        else
        {
            for (var i = 0; i < polygon.Count; i++)
            {
                points.Add2(polygon[i][0], polygon[i][1], 0.0);
            }
        }
        var result = set.SetPoints(points);
        if (result != 0)
        {
            throw new InvalidOperationException("SetPoints returned " + result + " on " + floorLabel);
        }
        Console.WriteLine(
            "AREA	{0}	{1}	{2} vertices	{3:F0} sq ft",
            floorLabel, propertyLabel, polygon.Count, Math.Abs(Area(polygon)) / 144.0);
    }

    private static void PlacePerimeter(
        IModel model, string floorLabel, int propertyUid, string propertyLabel, Dictionary<string, string> options)
    {
        const double lineTolerance = 1.2; // inches
        var floor = FindFloorType(model, floorLabel);
        var polygon = LargestPerimeter(floor, floorLabel);
        var skipX = options.ContainsKey("skip_x") ? Number(options, "skip_x") * 12.0 : double.NaN;
        var skipY = options.ContainsKey("skip_y") ? Number(options, "skip_y") * 12.0 : double.NaN;
        var sets = floor.GetLineLoadSets();
        var count = 0;
        var length = 0.0;
        var skipped = 0.0;
        for (var i = 0; i < polygon.Count; i++)
        {
            var a = polygon[i];
            var b = polygon[(i + 1) % polygon.Count];
            var edge = Math.Sqrt(Math.Pow(b[0] - a[0], 2) + Math.Pow(b[1] - a[1], 2));
            if (edge < MinEdgeInches)
            {
                continue;
            }
            var onSkipX = !double.IsNaN(skipX)
                && Math.Abs(a[0] - skipX) < lineTolerance && Math.Abs(b[0] - skipX) < lineTolerance;
            var onSkipY = !double.IsNaN(skipY)
                && Math.Abs(a[1] - skipY) < lineTolerance && Math.Abs(b[1] - skipY) < lineTolerance;
            if (onSkipX || onSkipY)
            {
                skipped += edge;
                continue;
            }
            sets.Add(propertyUid, a[0], a[1], b[0], b[1]);
            count++;
            length += edge;
        }
        Console.WriteLine(
            "PERIMETER	{0}	{1}	{2} line loads	{3:F1} ft loaded	{4:F1} ft skipped",
            floorLabel, propertyLabel, count, length / 12.0, skipped / 12.0);
    }

    private static double Area(List<double[]> polygon)
    {
        var sum = 0.0;
        for (var i = 0; i < polygon.Count; i++)
        {
            var a = polygon[i];
            var b = polygon[(i + 1) % polygon.Count];
            sum += a[0] * b[1] - b[0] * a[1];
        }
        return sum / 2.0;
    }

    private static void Report(IModel model)
    {
        var stories = model.GetStories();
        for (var i = 0; i < stories.GetCount(); i++)
        {
            var story = stories.GetAt(i);
            var type = story.GetFloorType();
            Console.WriteLine("STORY\t{0}\tfloor type {1} (UID {2})", story.strLabel, type.strLabel, type.lUID);
        }

        var types = model.GetFloorTypes();
        for (var i = 0; i < types.GetCount(); i++)
        {
            var type = types.GetAt(i);
            var perimeters = type.GetSlabPerimeters();
            var outline = new List<string>();
            for (var p = 0; p < perimeters.GetCount(); p++)
            {
                var polygon = Vertices(perimeters.GetAt(p));
                var length = 0.0;
                for (var v = 0; v < polygon.Count; v++)
                {
                    var a = polygon[v];
                    var b = polygon[(v + 1) % polygon.Count];
                    length += Math.Sqrt(Math.Pow(b[0] - a[0], 2) + Math.Pow(b[1] - a[1], 2));
                }
                outline.Add(string.Format(
                    CultureInfo.InvariantCulture,
                    "{0} vertices, {1:F0} sq ft, {2:F1} ft edge",
                    polygon.Count, Math.Abs(Area(polygon)) / 144.0, length / 12.0));
            }
            Console.WriteLine(
                "FLOOR_TYPE\t{0}\tUID {1}\twalls {2}\tcolumns {3}\tsurface loads {4}\tline loads {5}\tperimeters: {6}",
                type.strLabel, type.lUID, type.GetLayoutWalls().GetCount(), type.GetLayoutColumns().GetCount(),
                type.GetSurfaceLoadSets2().GetCount(), type.GetLineLoadSets().GetCount(),
                string.Join("; ", outline.ToArray()));
        }

        var surfaces = model.GetSurfaceLoadPropertySets();
        for (var i = 0; i < surfaces.GetCount(); i++)
        {
            var s = surfaces.GetAt(i);
            Console.WriteLine(
                "SURFACE\t{0}\tDL {1:F1}\tLL {2:F1} {3}\tMass {4:F1}\tPartition {5:F1} psf",
                s.strLabel, s.dDeadLoad / PsfToKsi, s.dLiveLoad / PsfToKsi, s.eLiveLoadType,
                s.dMassDeadLoad / PsfToKsi, s.dPartitionLoad / PsfToKsi);
        }
        var lines = model.GetLineLoadPropertySets();
        for (var i = 0; i < lines.GetCount(); i++)
        {
            var l = lines.GetAt(i);
            Console.WriteLine(
                "LINE\t{0}\tDL {1:F3}\tLL {2:F3}\tMass {3:F3} k/ft",
                l.strLabel, l.dDeadLoad / KlfToKpi, l.dLiveLoad / KlfToKpi, l.dMassDeadLoad / KlfToKpi);
        }
    }
}
