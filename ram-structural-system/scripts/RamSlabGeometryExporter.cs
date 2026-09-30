using System;
using System.Globalization;
using System.IO;
using System.Threading;
using RAMDATAACCESSLib;

internal static class RamSlabGeometryExporter
{
    private static TextWriter output = Console.Out;

    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length < 1 || args.Length > 2)
        {
            Console.Error.WriteLine(
                "Usage: RamSlabGeometryExporter.exe MODEL.rss [OUTPUT.tsv]");
            return 2;
        }

        var source = Path.GetFullPath(args[0]);
        if (!File.Exists(source))
        {
            Console.Error.WriteLine("Model not found: " + source);
            return 2;
        }

        IDBIO1 database = null;
        StreamWriter fileOutput = null;
        try
        {
            if (args.Length == 2)
            {
                var outputPath = Path.GetFullPath(args[1]);
                fileOutput = new StreamWriter(outputPath, false);
                output = fileOutput;
            }

            var dataAccess = new RamDataAccess1Class();
            database = (IDBIO1)dataAccess.GetDispInterfacePointerByEnum(
                EINTERFACES.IDBIO1_INT);

            database.LoadDataBase2(source, "AgenticRAM_SlabGeometry_ReadOnly");

            string conceptLinkPath = "";
            database.iTAS_GetConceptISMLinkFilePath(ref conceptLinkPath);

            var model = (IModel)dataAccess.GetDispInterfacePointerByEnum(
                EINTERFACES.IModel_INT);
            var floorTypes = model.GetFloorTypes();

            WriteRow("MODEL", source, "INTERNAL_LENGTH_UNITS", "in");
            WriteRow("CONCEPT_LINK", conceptLinkPath);
            WriteRow("FLOOR_COUNT", floorTypes.GetCount());

            for (var floorIndex = 0;
                 floorIndex < floorTypes.GetCount();
                 floorIndex++)
            {
                var floor = floorTypes.GetAt(floorIndex);
                var perimeters = floor.GetSlabPerimeters();
                var walls = floor.GetLayoutWalls();

                WriteRow(
                    "FLOOR",
                    floorIndex,
                    floor.lUID,
                    floor.strLabel,
                    "PERIMETERS",
                    perimeters.GetCount(),
                    "WALLS",
                    walls.GetCount());

                for (var perimeterIndex = 0;
                     perimeterIndex < perimeters.GetCount();
                     perimeterIndex++)
                {
                    var perimeter = perimeters.GetAt(perimeterIndex);
                    var vertices = perimeter.GetPerimeterVertices();
                    var edges = perimeter.GetEdges();

                    WriteRow(
                        "PERIMETER",
                        floorIndex,
                        perimeterIndex,
                        perimeter.lUID,
                        "VERTICES",
                        vertices.GetCount(),
                        "EDGES",
                        edges.GetCount());

                    for (var vertexIndex = 0;
                         vertexIndex < vertices.GetCount();
                         vertexIndex++)
                    {
                        var vertex = vertices.GetAt(vertexIndex);
                        var coordinate = new SCoordinate();
                        vertex.GetCoordinate(ref coordinate);

                        WriteRow(
                            "VERTEX",
                            floorIndex,
                            perimeterIndex,
                            vertexIndex,
                            coordinate.dXLoc,
                            coordinate.dYLoc,
                            coordinate.dZLoc);
                    }

                    for (var edgeIndex = 0;
                         edgeIndex < edges.GetCount();
                         edgeIndex++)
                    {
                        var edge = edges.GetAt(edgeIndex);
                        double startX = 0;
                        double startY = 0;
                        double endX = 0;
                        double endY = 0;
                        edge.GetCoordinates(
                            out startX,
                            out startY,
                            out endX,
                            out endY);

                        WriteRow(
                            "EDGE",
                            floorIndex,
                            perimeterIndex,
                            edgeIndex,
                            startX,
                            startY,
                            endX,
                            endY,
                            edge.dOffset);
                    }
                }

                for (var wallIndex = 0;
                     wallIndex < walls.GetCount();
                     wallIndex++)
                {
                    var wall = walls.GetAt(wallIndex);
                    double startX = 0;
                    double startY = 0;
                    double startZTop = 0;
                    double startZBottom = 0;
                    double endX = 0;
                    double endY = 0;
                    double endZTop = 0;
                    double endZBottom = 0;
                    wall.GetLayoutCoordinates(
                        out startX,
                        out startY,
                        out startZTop,
                        out startZBottom,
                        out endX,
                        out endY,
                        out endZTop,
                        out endZBottom);

                    WriteRow(
                        "WALL",
                        floorIndex,
                        wallIndex,
                        wall.lUID,
                        wall.lLabel,
                        startX,
                        startY,
                        endX,
                        endY,
                        wall.dThickness,
                        wall.lEccentricity,
                        wall.dEccDistance,
                        wall.eMaterial.ToString());
                }
            }

            output.Flush();
            return 0;
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine(exception);
            return 1;
        }
        finally
        {
            if (database != null)
            {
                var databaseToClose = database;
                var closeThread = new Thread(delegate()
                {
                    try
                    {
                        databaseToClose.CloseDatabase();
                    }
                    catch
                    {
                        // The process is exiting; retain the original exception.
                    }
                });
                closeThread.IsBackground = true;
                closeThread.Start();
                closeThread.Join(5000);
            }

            if (fileOutput != null)
            {
                fileOutput.Dispose();
                output = Console.Out;
            }
        }
    }

    private static void WriteRow(params object[] values)
    {
        for (var index = 0; index < values.Length; index++)
        {
            if (index > 0)
                output.Write('\t');

            var value = values[index];
            if (value is double)
            {
                output.Write(
                    ((double)value).ToString(
                        "R",
                        CultureInfo.InvariantCulture));
            }
            else
            {
                var text = value == null ? "" : value.ToString();
                output.Write(
                    text.Replace("\t", " ").Replace("\r", " ").Replace("\n", " "));
            }
        }
        output.WriteLine();
    }
}
