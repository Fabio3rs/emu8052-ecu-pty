#include "lab/LabButtons.hpp"
#include "lab/MeshAsset.hpp"

#include <gtest/gtest.h>

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
    EXPECT_FALSE(lab::lab_buttons_visible(899, 620));
    EXPECT_FALSE(lab::lab_buttons_visible(900, 619));
    for (std::size_t index = 0; index < lab::lab_button_labels.size();
         ++index) {
        const auto box = lab::lab_button_rect(index, 1280, 720);
        EXPECT_EQ(lab::hit_test_lab_button(box.x + box.width / 2.0f,
                                           box.y + box.height / 2.0f, 1280,
                                           720),
                  static_cast<lab::LabButtonAction>(index));
    }
    EXPECT_EQ(lab::hit_test_lab_button(20.0f, 560.0f, 1280, 720),
              lab::LabButtonAction::None);
    EXPECT_EQ(lab::hit_test_lab_button(20.0f, 504.0f, 500, 400),
              lab::LabButtonAction::None);
}
