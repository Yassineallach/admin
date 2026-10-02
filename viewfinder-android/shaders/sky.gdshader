shader_type sky;
// Pastel painted sky with drifting clouds and a soft sun, fading into a hazy
// sea horizon below.

uniform vec3 top_color : source_color = vec3(0.36, 0.62, 0.93);
uniform vec3 horizon_color : source_color = vec3(1.0, 0.86, 0.78);
uniform vec3 below_color : source_color = vec3(0.60, 0.74, 0.86);
uniform vec3 cloud_color : source_color = vec3(1.0, 0.97, 0.95);
uniform vec3 cloud_shade : source_color = vec3(0.92, 0.84, 0.92);
uniform float cloud_cover = 0.6;

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
	for (int i = 0; i < 3; i++) {
		s += a * vnoise(p);
		p = p * 2.07 + vec2(11.3, 4.7);
		a *= 0.5;
	}
	return s * 1.1;
}

void sky() {
	vec3 d = EYEDIR;
	float h = d.y;
	vec3 col = mix(horizon_color, top_color, smoothstep(0.0, 0.55, h));
	col = mix(col, below_color, smoothstep(0.0, -0.25, h));

	vec3 sun = LIGHT0_DIRECTION;
	float sd = max(dot(d, sun), 0.0);
	col += vec3(1.0, 0.9, 0.75) * (pow(sd, 8.0) * 0.18 + pow(sd, 400.0) * 1.2);

	if (h > 0.0) {
		vec2 p = d.xz / (h + 0.12) * 0.9 + vec2(TIME * 0.004, TIME * 0.002);
		float n = fbm(p);
		float cov = smoothstep(cloud_cover, cloud_cover + 0.12, n) * smoothstep(0.02, 0.2, h);
		float shade = smoothstep(cloud_cover, cloud_cover + 0.45, n * 1.05 - 0.02);
		vec3 cc = mix(cloud_color, cloud_shade, shade * 0.6);
		col = mix(col, cc, cov * 0.95);
	}
	COLOR = col;
}
