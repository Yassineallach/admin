shader_type spatial;
// Energy gate: additive shimmering field with scrolling scanlines, a hex
// lattice and bright edges.
render_mode unshaded, blend_add, cull_disabled, depth_draw_never;

uniform vec4 tint : source_color = vec4(1.0, 0.55, 0.3, 1.0);
uniform float strength = 1.0;

float hex_edge(vec2 p) {
	p *= vec2(1.0, 1.1547);
	vec2 a = mod(p, vec2(1.0, 1.732)) - vec2(0.5, 0.866);
	vec2 b = mod(p + vec2(0.5, 0.866), vec2(1.0, 1.732)) - vec2(0.5, 0.866);
	vec2 g = dot(a, a) < dot(b, b) ? a : b;
	vec2 q = abs(g);
	float d = max(q.x * 0.866 + q.y * 0.5, q.y);
	return smoothstep(0.42, 0.47, d);
}

void fragment() {
	vec2 uv = UV * vec2(3.0, 4.0);
	float scan = 0.5 + 0.5 * sin(UV.y * 60.0 - TIME * 6.0);
	float hex = hex_edge(uv * 2.0 + vec2(0.0, TIME * 0.15));
	float edge = 1.0 - smoothstep(0.0, 0.06, min(min(UV.x, 1.0 - UV.x), min(UV.y, 1.0 - UV.y)));
	float fres = pow(1.0 - abs(dot(NORMAL, VIEW)), 2.0);
	float a = 0.12 + 0.18 * scan + 0.5 * hex + 0.8 * edge + 0.4 * fres;
	ALBEDO = tint.rgb * a * strength;
}
