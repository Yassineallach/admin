shader_type sky;
// Bright cartoon sky: deep blue zenith, pale cyan horizon, big chunky
// cumulus clouds with lavender undersides, and a sparkling turquoise ocean
// far below the floating islands.

uniform vec3 top_color : source_color = vec3(0.10, 0.42, 0.98);
uniform vec3 horizon_color : source_color = vec3(0.66, 0.88, 1.0);
uniform vec3 cloud_color : source_color = vec3(1.0, 1.0, 1.0);
uniform vec3 cloud_shade : source_color = vec3(0.70, 0.74, 0.95);
uniform vec3 sea_near : source_color = vec3(0.02, 0.36, 0.62);
uniform vec3 sea_far : source_color = vec3(0.20, 0.72, 0.85);
uniform float cloud_cover = 0.58;

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
		p = p * 2.03 + vec2(11.3, 4.7);
		a *= 0.5;
	}
	return s * 1.07;
}

void sky() {
	vec3 d = EYEDIR;
	float h = d.y;
	vec3 col = mix(horizon_color, top_color, pow(smoothstep(0.0, 0.7, h), 0.7));

	vec3 sun = LIGHT0_DIRECTION;
	float sd = max(dot(d, sun), 0.0);
	col += vec3(1.0, 0.95, 0.8) * (pow(sd, 6.0) * 0.25 + smoothstep(0.9985, 0.9995, sd) * 2.0);

	if (h > 0.0) {
		vec2 p = d.xz / (h + 0.1) * 0.45 + vec2(TIME * 0.006, TIME * 0.003);
		float n = fbm(p);
		// Chunky, well-defined puffs with a soft cartoon edge.
		float cov = smoothstep(cloud_cover, cloud_cover + 0.05, n) * smoothstep(0.0, 0.12, h);
		// Lit tops, lavender bellies: compare with the noise a bit sunward.
		float lit = smoothstep(-0.04, 0.06, n - fbm(p - sun.xz * 0.06));
		vec3 cc = mix(cloud_shade, cloud_color, 0.35 + 0.65 * lit);
		col = mix(col, cc, cov);
	} else {
		// Ocean far below, with sun glints and a pale haze at the horizon.
		vec2 p = d.xz / (-h + 0.02) * 2.0 + vec2(TIME * 0.02, 0.0);
		float w = vnoise(p * 3.0) * 0.6 + vnoise(p * 7.0 + 3.0) * 0.4;
		vec3 sea = mix(sea_near, sea_far, smoothstep(-0.6, 0.0, h));
		sea *= 0.92 + 0.15 * w;
		sea += vec3(1.0) * smoothstep(0.82, 0.9, w) * 0.25 * smoothstep(-0.5, -0.02, h);
		col = mix(sea, horizon_color, smoothstep(-0.06, 0.0, h));
	}
	COLOR = col;
}
