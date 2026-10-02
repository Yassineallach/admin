shader_type spatial;
// World shader for every sliceable surface.
//   UV   = texture coordinates in metres (frame travels with the geometry)
//   UV2  = (material id, art style id)  -> see scripts/geometry/mat.gd
//   COLOR= per-face tint
// Procedural textures keep the APK small and stay crisp at any distance.
// Soft half-lambert lighting + lifted shadows give the pastel, airy look.

render_mode cull_back, specular_disabled;

uniform float shadow_floor = 0.42;

varying vec2 v_uv;
varying vec3 v_wpos;
varying float v_style;
varying float v_mat;
varying vec3 v_bary;
varying float v_mask;

float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash12(i), hash12(i + vec2(1, 0)), u.x),
		mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), u.x), u.y);
}

float fbm(vec2 p) {
	float a = 0.5;
	float s = 0.0;
	for (int i = 0; i < 4; i++) {
		s += a * vnoise(p);
		p = p * 2.03 + vec2(17.1, 9.2);
		a *= 0.5;
	}
	return s;
}

vec3 srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}

float luma(vec3 c) {
	return dot(c, vec3(0.299, 0.587, 0.114));
}

void vertex() {
	if (int(UV2.x + 0.5) == 8) {
		// Leaves sway gently in the wind.
		vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		float ph = TIME * 1.4 + w.x * 0.35 + w.z * 0.27;
		VERTEX += vec3(sin(ph), sin(ph * 1.7) * 0.4, cos(ph * 0.9)) * 0.045;
	}
	v_uv = UV;
	v_wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_mat = UV2.x;
	v_style = UV2.y;
	v_bary = CUSTOM0.xyz;
	v_mask = CUSTOM0.w;
}

// Distance in pixels to the nearest real polygon edge of this face.
float edge_px() {
	int m = int(v_mask + 0.5);
	vec3 fw = max(fwidth(v_bary), vec3(1e-5));
	vec3 px = v_bary / fw;
	float d = 1e4;
	if ((m & 1) != 0) d = min(d, px.x);
	if ((m & 2) != 0) d = min(d, px.y);
	if ((m & 4) != 0) d = min(d, px.z);
	return d;
}

// Small round "spot" in a jittered grid: returns (mask, cell random).
vec2 spots(vec2 uv, float density, float radius) {
	vec2 id = floor(uv);
	vec2 f = fract(uv);
	float r = hash12(id);
	vec2 c = vec2(hash12(id + 7.3), hash12(id + 3.1)) * 0.6 + 0.2;
	float m = step(1.0 - density, r) * (1.0 - smoothstep(radius * 0.7, radius, length(f - c)));
	return vec2(m, hash12(id + 11.7));
}

vec3 material_color(int m, vec2 uv, vec3 base, out float emit) {
	emit = 0.0;
	vec3 c = base;
	if (m == 0) { // plaster: soft mottling + faint vertical weathering streaks
		c *= 0.95 + 0.07 * fbm(uv * 2.5);
		c *= 0.97 + 0.04 * vnoise(vec2(uv.x * 6.0, uv.y * 0.4));
	} else if (m == 1) { // grass: tonal patches, clover, little flowers
		float n = fbm(uv * 0.8);
		float speck = hash12(floor(uv * 28.0));
		c *= 0.80 + 0.32 * n + 0.08 * speck;
		c = mix(c, c * vec3(1.08, 1.1, 0.8), smoothstep(0.55, 0.8, fbm(uv * 0.3 + 7.0)));
		c = mix(c, c * vec3(0.82, 0.95, 0.85), smoothstep(0.6, 0.75, vnoise(uv * 1.7 + 3.0)) * 0.6);
		vec2 fl = spots(uv * 3.2, 0.11, 0.2);
		vec3 petal = fl.y < 0.33 ? vec3(1.0, 0.98, 0.95) : (fl.y < 0.66 ? vec3(1.0, 0.62, 0.72) : vec3(1.0, 0.86, 0.35));
		c = mix(c, srgb_to_linear(petal), fl.x);
		vec2 fl2 = spots(uv * 3.2 + 0.5, 0.11, 0.07);
		c = mix(c, srgb_to_linear(vec3(1.0, 0.85, 0.3)), fl2.x * fl.x);
	} else if (m == 2) { // stone tiles (1 m) with mossy grout, wear and the odd crack
		vec2 id = floor(uv);
		vec2 f = fract(uv);
		float edge = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y));
		float h = hash12(id);
		c *= 0.9 + 0.14 * h + 0.05 * vnoise(uv * 6.0);
		c *= 1.0 + 0.05 * (1.0 - smoothstep(0.1, 0.45, length(f - 0.5)));
		float grout = 1.0 - smoothstep(0.015, 0.04, edge);
		vec3 moss = srgb_to_linear(vec3(0.55, 0.68, 0.42));
		float mossy = smoothstep(0.45, 0.75, fbm(uv * 1.3 + 4.0));
		c = mix(c, mix(c * 0.72, moss, mossy), grout);
		if (h > 0.86) {
			float crack = abs(f.y - 0.5 - 0.25 * sin(f.x * 7.0 + h * 20.0) * (f.x - 0.5));
			c *= mix(0.8, 1.0, smoothstep(0.004, 0.012, crack));
		}
	} else if (m == 3) { // bricks with colour variety, recessed mortar, weathering
		vec2 b = uv / vec2(0.5, 0.22);
		float row = floor(b.y);
		b.x += mod(row, 2.0) * 0.5;
		vec2 id = floor(b);
		vec2 f = fract(b);
		float edge = min(min(f.x, 1.0 - f.x) * 0.5, min(f.y, 1.0 - f.y) * 0.22);
		float h = hash12(id);
		c *= 0.82 + 0.24 * h + 0.05 * vnoise(uv * 9.0);
		if (h > 0.9) c *= vec3(1.05, 0.92, 0.88);
		c *= 1.0 - 0.06 * smoothstep(0.02, 0.0, f.y);  // bottom shadow of each brick
		c *= 0.94 + 0.08 * vnoise(vec2(uv.x * 3.0, uv.y * 0.25));
		c = mix(base * vec3(1.12, 1.1, 1.06) * 0.92, c, smoothstep(0.006, 0.016, edge));
	} else if (m == 4 || m == 10) { // wood / planks with grain and nail heads
		float w = m == 4 ? 0.22 : 0.3;
		float plank = floor(uv.y / w);
		float f = fract(uv.y / w);
		float grain = sin((uv.x + hash12(vec2(plank, 3.0)) * 10.0) * 9.0 + fbm(uv * vec2(1.5, 14.0)) * 6.0);
		c *= 0.86 + 0.12 * hash12(vec2(plank, 1.0)) + 0.04 * grain;
		c *= mix(0.7, 1.0, smoothstep(0.0, 0.06, min(f, 1.0 - f)));
		float knot = 1.0 - smoothstep(0.0, 0.05, length(vec2(fract(uv.x * 0.7 + hash12(vec2(plank, 5.0))) - 0.5, f - 0.5) * vec2(1.0, w * 3.0)));
		c *= 1.0 - 0.25 * knot * step(0.6, hash12(vec2(plank, 9.0)));
		// Nail pairs where boards cross a joist (every ~1.6 m, staggered per board).
		float nx = fract(uv.x / 1.6 + hash12(vec2(plank, 2.0)) * 0.15) * 1.6;
		vec2 nail = vec2(nx, f * w);
		float nails = 1.0 - smoothstep(0.008, 0.013, min(length(nail - vec2(0.05, w * 0.28)), length(nail - vec2(0.05, w * 0.72))));
		c = mix(c, c * 0.6, nails * float(m == 10));
	} else if (m == 5) { // water
		float t = TIME * 0.6;
		float wv = fbm(uv * 0.35 + vec2(t * 0.15, t * 0.1)) + fbm(uv * 0.9 - vec2(t * 0.1, -t * 0.07));
		c *= 0.82 + 0.25 * wv;
		float spark = smoothstep(0.86, 0.95, fbm(uv * 1.7 + vec2(t * 0.3, 0.0)));
		emit = spark * 0.45;
	} else if (m == 6) { // roof shingles with moss specks
		vec2 b = uv / vec2(0.35, 0.25);
		b.x += mod(floor(b.y), 2.0) * 0.5;
		vec2 f = fract(b);
		float scallop = length(vec2(f.x - 0.5, (f.y) * 0.9));
		c *= 0.85 + 0.12 * hash12(floor(b));
		c *= mix(0.78, 1.0, smoothstep(0.5, 0.42, scallop));
		c = mix(c, srgb_to_linear(vec3(0.6, 0.7, 0.45)), smoothstep(0.7, 0.85, fbm(uv * 1.2)) * 0.5);
	} else if (m == 7) { // metal
		c *= 0.9 + 0.1 * vnoise(uv * vec2(1.0, 30.0));
	} else if (m == 8) { // foliage: leafy clusters
		float n = fbm(uv * 1.6);
		c *= 0.72 + 0.45 * n;
		vec2 lf = spots(uv * 6.0, 0.6, 0.35);
		c *= 1.0 + 0.12 * lf.x * (lf.y - 0.3);
		c *= 0.92 + 0.12 * hash12(floor(uv * 14.0));
	} else if (m == 9) { // rock with strata and lichen
		float strata = sin(uv.y * 3.0 + fbm(uv * 0.7) * 4.0);
		c *= 0.76 + 0.22 * fbm(uv * 0.9) + 0.06 * strata;
		float lichen = smoothstep(0.62, 0.72, fbm(uv * 1.4 + 9.0)) * smoothstep(0.4, 0.6, vnoise(uv * 7.0));
		c = mix(c, srgb_to_linear(vec3(0.74, 0.8, 0.56)), lichen * 0.35);
	} else if (m == 11) { // glow
		emit = 2.0;
	} else if (m == 12) { // archive stone: dark slate blocks with glowing rune seams
		vec2 b = uv / vec2(1.0, 0.5);
		b.x += mod(floor(b.y), 2.0) * 0.5;
		vec2 f = fract(b);
		float edge = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y) * 0.5);
		c = srgb_to_linear(vec3(0.27, 0.28, 0.36)) * (0.85 + 0.25 * hash12(floor(b)) + 0.08 * vnoise(uv * 5.0));
		float seam = 1.0 - smoothstep(0.0, 0.02, edge);
		float pulse = 0.6 + 0.4 * sin(TIME * 1.5 + uv.x * 0.6 + uv.y * 0.4);
		vec3 glow_col = srgb_to_linear(vec3(0.45, 0.85, 1.0));
		c = mix(c, glow_col * 0.6, seam);
		emit = seam * 1.2 * pulse;
		// Occasional carved rune: a small glowing ring inside a block.
		vec2 rid = floor(b);
		float has_rune = step(0.88, hash12(rid + 5.0));
		float ring = abs(length((f - 0.5) * vec2(2.0, 1.0)) - 0.22);
		float rune = has_rune * (1.0 - smoothstep(0.015, 0.035, ring));
		emit += rune * 1.0 * pulse;
		c = mix(c, glow_col, rune * 0.6);
	}
	return c;
}

void fragment() {
	int m = int(v_mat + 0.5);
	int st = int(v_style + 0.5);
	vec3 base = srgb_to_linear(COLOR.rgb);
	float emit;
	vec3 c = material_color(m, v_uv, base, emit);

	if (st == 1) { // pencil sketch on paper
		float detail = clamp(luma(c) / max(luma(base), 0.001), 0.0, 1.2);
		float pencil = mix(0.45, 1.0, smoothstep(0.72, 0.97, detail));
		float paper = 0.94 + 0.05 * vnoise(v_uv * 40.0);
		// Wobbly graphite outline along every face edge + silhouettes.
		float wob = 1.2 + 1.1 * vnoise(v_uv * 3.0 + v_wpos.xy);
		float line = 1.0 - smoothstep(wob * 0.5, wob, edge_px());
		float sil = 1.0 - smoothstep(0.12, 0.3, abs(dot(NORMAL, VIEW)));
		float ink = max(line, sil * 0.8);
		vec3 paper_col = vec3(0.95, 0.93, 0.88) * paper * pencil;
		c = mix(paper_col, vec3(0.28, 0.27, 0.32), ink * 0.85);
		emit = 0.0;
	} else if (st == 2) { // watercolour
		vec2 q = v_uv * 0.32 + v_wpos.xz * 0.025;
		float wash = fbm(q);
		float wash2 = fbm(v_uv * 0.9 + vec2(3.0, 7.0));
		// Soften the material detail into a flat wash of the base colour.
		c = mix(c, base * (0.9 + 0.2 * luma(c) / max(luma(base), 0.01)), 0.5);
		vec3 g = vec3(luma(c));
		c = mix(g, c, 1.9);
		// Colour drifts: warm and cool pigments wander across each surface.
		c *= mix(vec3(1.08, 0.9, 0.82), vec3(0.82, 0.94, 1.1), smoothstep(0.3, 0.7, wash2));
		c *= 0.7 + 0.5 * wash;
		// Blooms: dark wet rings where washes dried.
		float ring = abs(fract(wash * 5.0) - 0.5);
		c *= mix(0.82, 1.0, smoothstep(0.0, 0.06, ring));
		// Pigment pools along edges; dry-brush gaps let the paper through.
		float e = edge_px();
		c *= mix(0.5, 1.0, smoothstep(0.0, 10.0 + 8.0 * vnoise(v_uv * 4.0), e));
		c = mix(c, vec3(0.99, 0.97, 0.92), 0.45 * smoothstep(0.6, 0.8, vnoise(v_uv * 0.7 + wash * 2.0)));
		c *= 0.9 + 0.12 * vnoise(v_uv * 38.0);
	} else if (st == 0) {
		// Soft bevel: a hint of light along every edge gives a crafted, model-kit feel.
		c *= 1.0 + 0.10 * (1.0 - smoothstep(0.6, 2.6, edge_px()));
	} else if (st == 3) { // sepia
		float l = luma(c);
		c = vec3(l * 1.07, l * 0.95, l * 0.78);
		c *= mix(0.85, 1.0, smoothstep(0.0, 2.0, edge_px()));
	}

	ALBEDO = clamp(c, 0.0, 1.0);
	EMISSION = c * emit;
	ROUGHNESS = 1.0;
}

void light() {
	int st = int(v_style + 0.5);
	float ndl = dot(NORMAL, LIGHT);
	float shadow = mix(shadow_floor, 1.0, ATTENUATION);
	if (st == 1) {
		// Cross-hatching instead of smooth shading.
		float lit = clamp(ndl, 0.0, 1.0) * ATTENUATION;
		float h1 = step(0.55, fract((v_uv.x + v_uv.y) * 7.0));
		float h2 = step(0.55, fract((v_uv.x - v_uv.y) * 7.0));
		float tone = 1.0;
		if (lit < 0.55) tone -= 0.28 * h1;
		if (lit < 0.2) tone -= 0.22 * h2;
		DIFFUSE_LIGHT += LIGHT_COLOR / PI * tone;
	} else {
		float wrap = clamp(ndl * 0.55 + 0.45, 0.0, 1.0);
		if (st == 2) {
			wrap = floor(wrap * 3.0 + 0.5) / 3.0;
		}
		DIFFUSE_LIGHT += LIGHT_COLOR / PI * wrap * wrap * shadow;
	}
}
