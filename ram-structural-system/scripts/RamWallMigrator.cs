using System;
using RAMDATAACCESSLib;

internal static class RamWallMigrator
{
    private static int Main(string[] args)
    {
        try
        {
            var rda = new RamDataAccess1Class();
            var model = (IModel)rda.GetDispInterfacePointerByEnum(EINTERFACES.IModel_INT);
            var floorTypes = model.GetFloorTypes();

            Console.WriteLine("Floor types: " + floorTypes.GetCount());
            for (var i = 0; i < floorTypes.GetCount(); i++)
            {
                var floor = floorTypes.GetAt(i);
                Console.WriteLine("[{0}] UID={1} Label={2} Walls={3} SlabEdges={4}",
                    i, floor.lUID, floor.strLabel, floor.GetLayoutWalls().GetCount(),
                    floor.GetAllSlabEdges().GetCount());
            }
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.ToString());
            return 1;
        }
    }
}
