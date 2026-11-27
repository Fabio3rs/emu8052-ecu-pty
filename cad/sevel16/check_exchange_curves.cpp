// Measure OCCT curve-on-surface discrepancies on the B-rep actually read from STEP.
#include <BOPAlgo_ArgumentAnalyzer.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <BRepBndLib.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <iomanip>
#include <iostream>
#include <string_view>

int main(int argc, char** argv) {
    const bool intersections = argc == 3 && std::string_view(argv[2]) == "--intersections";
    if (argc != 2 && !intersections) return 2;
    TopoDS_Shape shape;
    BRep_Builder builder;
    if (!BRepTools::Read(shape, argv[1], builder) || shape.IsNull()) return 1;
    TopTools_IndexedMapOfShape faces, edges;
    TopExp::MapShapes(shape, TopAbs_FACE, faces);
    TopExp::MapShapes(shape, TopAbs_EDGE, edges);
    BOPAlgo_ArgumentAnalyzer analyzer;
    analyzer.SetShape1(shape);
    analyzer.CurveOnSurfaceMode() = !intersections;
    analyzer.SelfInterMode() = intersections;
    analyzer.Perform();
    if (analyzer.HasErrors()) return 1;
    if (intersections) {
        TopTools_IndexedMapOfShape parts;
        TopExp::MapShapes(shape, parts);
        std::cout << "pair,shape_id,kind,face_id,xmin,ymin,zmin,xmax,ymax,zmax\n";
        unsigned pair = 0;
        for (const auto& result : analyzer.GetCheckResult()) {
            if (result.GetCheckStatus() != BOPAlgo_SelfIntersect) continue;
            ++pair;
            for (const auto& item : result.GetFaultyShapes1()) {
                Bnd_Box bounds;
                BRepBndLib::AddOptimal(item, bounds, false);
                const auto lo = bounds.CornerMin(), hi = bounds.CornerMax();
                std::cout << pair << ',' << parts.FindIndex(item) << ',' << item.ShapeType()
                          << ',' << faces.FindIndex(item) << ',' << lo.X() << ',' << lo.Y()
                          << ',' << lo.Z() << ',' << hi.X() << ',' << hi.Y() << ',' << hi.Z() << '\n';
            }
        }
        return 0;
    }
    std::cout << "face,edge,edge_tolerance_mm,deviation_mm,x_mm,y_mm,z_mm\n";
    std::cout << std::setprecision(15);
    for (const auto& result : analyzer.GetCheckResult()) {
        if (result.GetCheckStatus() != BOPAlgo_InvalidCurveOnSurface) continue;
        TopoDS_Edge edge;
        int face = 0;
        for (const auto& item : result.GetFaultyShapes1()) {
            if (item.ShapeType() == TopAbs_EDGE) edge = TopoDS::Edge(item);
            if (item.ShapeType() == TopAbs_FACE) face = faces.FindIndex(item);
        }
        if (edge.IsNull() || face == 0) return 1;
        BRepAdaptor_Curve curve(edge);
        const auto point = curve.Value(result.GetMaxParameter1());
        std::cout << face << ',' << edges.FindIndex(edge) << ',' << BRep_Tool::Tolerance(edge)
                  << ',' << result.GetMaxDistance1() << ',' << point.X() << ',' << point.Y()
                  << ',' << point.Z() << '\n';
    }
}
