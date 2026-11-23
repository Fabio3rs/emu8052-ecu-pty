// C++ stores row-major column-vector matrices. HLSL reads the transpose.
cbuffer VertexUniforms : register(b0, space1) {
    float4x4 model;
    float4x4 view;
    float4x4 projection;
    float4 deformation;
};
struct Vertex {
    float4 position : TEXCOORD0;
    float4 normal : TEXCOORD1;
    float2 uv : TEXCOORD2;
};
struct Surface {
    float4 position : SV_Position;
    float3 world : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float2 belt : TEXCOORD2;
};
Surface VSMain(Vertex input) {
    Surface output;
    input.position.y += input.uv.x * deformation.x;
    float4 world = mul(input.position, model);
    output.world = world.xyz;
    output.normal = mul(input.normal, model).xyz;
    output.belt = float2(input.uv.y-deformation.y, deformation.z);
    output.position = mul(mul(world, view), projection);
    return output;
}
cbuffer SurfaceUniforms : register(b0, space3) {
    float4 material;
    float4 cut;
    float4 secondCut;
};
float4 PSMain(Surface input) : SV_Target0 {
    clip(dot(cut, float4(input.world,1)));
    clip(dot(secondCut, float4(input.world,1)));
    float3 n = normalize(input.normal);
    float key = saturate(dot(n, normalize(float3(-0.5,0.85,0.65))));
    float fill = saturate(dot(n, normalize(float3(0.7,0.35,-0.7))));
    float light = 0.32 + 0.63*key + 0.28*fill;
    if (input.belt.y > 0)
        light *= 0.75 + 0.38 * smoothstep(0.12,0.32,abs(frac(input.belt.x)-0.5));
    // Compress the display contrast to preserve the ribs in dark castings.
    return float4(pow(saturate(material.rgb * light), 0.79), material.a);
}
