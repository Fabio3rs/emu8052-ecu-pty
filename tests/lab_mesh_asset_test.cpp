#include "lab/LabButtons.hpp"
#include "lab/MeshAsset.hpp"

#include <gtest/gtest.h>
#include <sstream>

TEST(LabMeshAsset, LoadsCadBatchNamesWithoutRequiringDonorParts) {
    const std::string obj = "v 0 0 0\nv 0.0864 0 0\nv 0 0.0674 0\n"
                            "vn 0 0 1\no batch_000\nf 1//1 2//1 3//1\n";
    AuthoredMeshLibrary library;
    std::istringstream cad(obj);
    ASSERT_TRUE(library.loadAll(cad));
    const auto *mesh = library.find("batch_000");
    ASSERT_NE(mesh, nullptr);
    ASSERT_EQ(mesh->vertices.size(), 3U);
    EXPECT_FLOAT_EQ(mesh->vertices[1].Pos.x, 0.0864f);
    EXPECT_FLOAT_EQ(mesh->vertices[2].Pos.y, 0.0674f);
    EXPECT_FLOAT_EQ(mesh->vertices[0].Normal.z, 1.0f);
    std::istringstream donor(obj);
    EXPECT_FALSE(library.load(donor));
}

TEST(LabMeshAsset, RejectsEmptyDuplicateAndInvalidCadBatches) {
    for (const std::string &text : {
             std::string("o batch_000\n"),
             std::string("o batch_000\no batch_000\n"),
             std::string("v 0 0 0\nvn 0 0 1\no batch_000\nf 1//1 2//1 3//1\n")}) {
        AuthoredMeshLibrary library;
        std::istringstream input(text);
        EXPECT_FALSE(library.loadAll(input));
    }
}

TEST(LabMeshAsset, LoadsOriginalDonorGeometry) {
    AuthoredMeshLibrary library;
    ASSERT_TRUE(lab::load_packaged_meshes(library, LAB_MESH_ASSET_PATH));
    for (const char *name :
         {"Piston", "ConnectingRod", "Crankshaft", "CylinderHead", "Valve",
          "CrankSnout", "CrankSnoutThreads", "Logo"}) {
        const auto *mesh = library.find(name);
        ASSERT_NE(mesh, nullptr) << name;
        EXPECT_GT(mesh->vertices.size(), 0U) << name;
        EXPECT_GT(mesh->indices.size(), 0U) << name;
        EXPECT_EQ(mesh->indices.size() % 3, 0U) << name;
    }
}

TEST(LabMeshAsset, RejectsMissingAsset) {
    AuthoredMeshLibrary library;
    EXPECT_FALSE(lab::load_packaged_meshes(library, "missing-mesh.b64"));
}

TEST(LabMeshAsset, DecodesUnmodifiedDonorFont) {
    const auto font = lab::decode_packaged_bytes(LAB_FONT_ASSET_PATH, 18336);
    ASSERT_EQ(font.size(), 18336U);
    EXPECT_EQ(font[0], 0U);
    EXPECT_EQ(font[1], 1U);
    EXPECT_EQ(font[2], 0U);
    EXPECT_EQ(font[3], 0U);
}

TEST(LabButtons, EveryVisibleControlHasAUniqueHitTarget) {
    EXPECT_TRUE(lab::lab_buttons_visible(900, 620));
    EXPECT_TRUE(lab::lab_buttons_visible(899, 620));
    EXPECT_TRUE(lab::lab_buttons_visible(900, 619));
    EXPECT_FALSE(lab::lab_buttons_visible(599, 620));
    EXPECT_FALSE(lab::lab_buttons_visible(900, 349));
    for (std::size_t index = 0; index < lab::lab_button_labels.size();
         ++index) {
        const auto box = lab::lab_button_rect(index, 1280, 720);
        EXPECT_EQ(lab::hit_test_lab_button(box.x + box.width / 2.0f,
                                           box.y + box.height / 2.0f, 1280,
                                           720),
                  static_cast<lab::LabButtonAction>(index));
    }
    EXPECT_EQ(lab::hit_test_lab_button(20.0f, 700.0f, 1280, 720),
              lab::LabButtonAction::None);
    EXPECT_EQ(lab::hit_test_lab_button(20.0f, 504.0f, 500, 400),
              lab::LabButtonAction::None);
}
