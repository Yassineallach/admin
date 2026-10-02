shader_type spatial;
// Imported CC0 art (Quaternius kits): base-colour texture, alpha-cut foliage,
// wind, the same soft lighting as the world, and the photo art styles.
render_mode cull_disabled, specular_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform vec4 albedo_color : source_color = vec4(1.0);
uniform float use_tex = 1.0;
uniform float alpha_cut = 0.0;
uniform float wind = 0.0;
uniform float recolor = 0.0;
uniform float style = 0.0;
uniform float shadow_floor = 0.42;

varying vec3 v_wpos;

float luma(vec3 c) {
	return dot(c, vec3(0.299, 0.587, 0.114));
}

float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	if (wind > 0.0) {
		float ph = TIME * 1.5 + w.x * 0.35 + w.z * 0.27;
		VERTEX += vec3(sin(ph), sin(ph * 1.7) * 0.3, cos(ph * 0.9)) * 0.04 * wind;
	}
	v_wpos = w;
}

void fragment() {
	vec4 t = mix(vec4(1.0), texture(albedo_tex, UV), use_tex) * mix(albedo_color, vec4(1.0), recolor);
	if (recolor > 0.5) {
		// Blossom: keep the texture's shading, take the hue from albedo_color.
		float l = luma(t.rgb);
		t.rgb = albedo_color.rgb * (0.35 + l * 1.9);
	}
	if (alpha_cut > 0.0 && t.a < alpha_cut) {
		discard;
	}
	vec3 c = t.rgb;
	int st = int(style + 0.5);
	if (st == 1) { // pencil
		float l = luma(c);
		float paper = 0.93 + 0.05 * hash12(floor(UV * 300.0));
		float sil = 1.0 - smoothstep(0.1, 0.3, abs(dot(NORMAL, VIEW)));
		c = vec3(0.95, 0.93, 0.88) * paper * mix(0.55, 1.0, smoothstep(0.15, 0.6, l));
		c = mix(c, vec3(0.28, 0.27, 0.32), sil * 0.8);
	} else if (st == 2) { // watercolour
		vec3 g = vec3(luma(c));
		c = mix(g, c, 1.6);
		c = mix(c, floor(c * 5.0 + 0.5) / 5.0, 0.5);
		c = mix(c, vec3(0.99, 0.97, 0.92), 0.12);
	} else if (st == 3) { // sepia
		float l = luma(c);
		c = vec3(l * 1.07, l * 0.95, l * 0.78);
	}
	ALBEDO = c;
	ROUGHNESS = 1.0;
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float wrap = clamp(ndl * 0.55 + 0.45, 0.0, 1.0);
	float shadow = mix(shadow_floor, 1.0, ATTENUATION);
	DIFFUSE_LIGHT += LIGHT_COLOR / PI * wrap * wrap * shadow;
}
