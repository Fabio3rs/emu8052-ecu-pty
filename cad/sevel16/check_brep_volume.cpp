// Evaluate trimmed B-spline solids with adaptive quadrature. All values in mm³.
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <GProp_GProps.hxx>
#include <TopoDS_Shape.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>

int main(int argc, char** argv) {
    if (argc < 2) return 2;
    for (int i = 1; i < argc; ++i) {
        TopoDS_Shape shape;
        BRep_Builder builder;
        if (!BRepTools::Read(shape, argv[i], builder) || shape.IsNull()) return 1;
        GProp_GProps props;
        const double error = BRepGProp::VolumePropertiesGK(shape, props, 1e-9, true, true);
        if (!std::isfinite(error) || error < 0) return 1;
        if (!std::isfinite(props.Mass()) || props.Mass() <= 0) return 1;
        std::cout << std::setprecision(17) << props.Mass() << '\n';
    }
}
