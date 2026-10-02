shader_type spatial;
// Pastel architectural look: flat vertex colours, soft 1 m tile lines in world
// space and a gentle rim tint. Works on the Compatibility (GLES3) renderer.

render_mode cull_back, diffuse_lambert, specular_disabled;

uniform float grid_strength = 0.10;
uniform float grid_width = 0.025;

varying vec3 world_pos;
varying vec3 world_nrm;

vec3 srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_nrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 an = abs(world_nrm);
	vec2 uv = an.y > 0.6 ? world_pos.xz : (an.x > an.z ? world_pos.zy : world_pos.xy);
	vec2 g = abs(fract(uv) - 0.5);
	float edge = max(g.x, g.y);
	float line = smoothstep(0.5 - grid_width, 0.5, edge);
	vec3 c = srgb_to_linear(COLOR.rgb);
	c *= 1.0 - line * grid_strength;
	ALBEDO = c;
	ROUGHNESS = 1.0;
}
