# RAM wall API map

Source of truth:

- `C:\Program Files\Bentley\Engineering\RAM Structural System\manuals\RAM DataAccess Developers Guide.pdf`
- `C:\Program Files\Bentley\Engineering\RAM Structural System\Prog\Interop.RAMDATAACCESSLib.dll`

## Typed interface path

1. Instantiate `RAMDATAACCESSLib.RamDataAccess1Class`.
2. Get `IDBIO1` with `GetInterfacePointerByEnum(IDBIO1_INT)`.
3. Confirm the live model using `IDBIO1.iTAS_GetLoadedModelPath`.
4. Get `IModel` with `GetInterfacePointerByEnum(IModel_INT)`.
5. Traverse `IModel.GetFloorTypes()` -> `IFloorType.GetLayoutWalls()`.

Do not use dynamic `GetDispInterfacePointerByEnum(IModel_INT)` from PowerShell. It caused an access violation in an isolated process on RAM Structural System 2025.

## Wall identity and location

- RAM floor types are the model's layout layers.
- `IFloorType.strLabel` identifies the floor type.
- `ILayoutWall.GetAssociatedStoryWalls()` identifies the actual story walls represented by a layout wall.
- `ILayoutWall.GetLayoutCoordinates()` returns start/end XY coordinates and top/bottom Z offsets.
- `ILayoutWall.lUID` is the UID accepted by `ILayoutWalls.Delete(lUID)`.

## Concrete material identification

- `EMATERIALTYPES.EWallPropConcreteMat` has value `5`.
- `EMATERIALTYPES.EWallPropOtherMat` has value `6`.
- `ILayoutWall.lMaterialID` is passed to `IModel.GetConcreteMaterial()` for a concrete wall.
- `IConcreteMaterial` exposes `dFpc`, `dElasticModulus`, `dUnitWeight`, `dSelfWeight`, `dPoissonsRatio`, and reinforcement yield strengths.

## Deletion behavior

`ILayoutWalls.Delete(layoutWallUID)` deletes the layout wall and all corresponding walls on stories associated with that floor type. Story-level `IWalls` does not expose deletion. After geometry changes, call `IModel.ClearSWData(0)` before saving.
