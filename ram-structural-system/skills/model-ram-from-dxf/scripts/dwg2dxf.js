// dwg2dxf.js: qcad.exe -no-gui -autostart dwg2dxf.js <in.dwg> <out.dxf>
function main() {
  var args = (typeof RSettings.getOriginalArguments === "function") ? RSettings.getOriginalArguments() : QCoreApplication.arguments();
  var input = args[args.length - 2];
  var output = args[args.length - 1];
  var doc = new RDocument(new RMemoryStorage(), new RSpatialIndexNavel());
  var di = new RDocumentInterface(doc);
  var err = di.importFile(input);
  if (err !== RDocumentInterface.IoErrorNoError) { qWarning("import failed (" + err + "): " + input); return 1; }
  var ok = di.exportFile(output, "R27 (2013) DXF");
  qWarning((ok ? "wrote " : "export failed ") + output);
  di.destroy();
  return ok ? 0 : 2;
}
main();
