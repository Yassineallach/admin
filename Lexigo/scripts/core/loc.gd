extends Node
## UI string table. The interface follows the player's native language;
## missing entries fall back to English.

const LANGS := ["en", "fr", "es", "de", "it", "pt"]

const STRINGS := {
	"tagline": ["Learn languages, one crossword at a time", "Apprends les langues, une grille à la fois", "Aprende idiomas, un crucigrama a la vez", "Sprachen lernen, ein Kreuzworträtsel nach dem anderen", "Impara le lingue, un cruciverba alla volta", "Aprenda idiomas, uma cruzadinha por vez"],
	"i_speak": ["I speak", "Je parle", "Hablo", "Ich spreche", "Parlo", "Eu falo"],
	"i_learn": ["I want to learn", "Je veux apprendre", "Quiero aprender", "Ich möchte lernen", "Voglio imparare", "Quero aprender"],
	"start": ["Let's go!", "C'est parti !", "¡Vamos!", "Los geht's!", "Andiamo!", "Vamos lá!"],
	"play": ["Play", "Jouer", "Jugar", "Spielen", "Gioca", "Jogar"],
	"daily": ["Daily", "Défi du jour", "Diario", "Täglich", "Del giorno", "Diário"],
	"daily_title": ["Daily Challenge", "Défi du jour", "Reto diario", "Tagesrätsel", "Sfida del giorno", "Desafio diário"],
	"daily_done": ["Come back tomorrow!", "Reviens demain !", "¡Vuelve mañana!", "Komm morgen wieder!", "Torna domani!", "Volte amanhã!"],
	"review": ["Review", "Révision", "Repaso", "Wiederholen", "Ripasso", "Revisão"],
	"review_title": ["Memory Review", "Révision mémoire", "Repaso de memoria", "Gedächtnistraining", "Ripasso di memoria", "Revisão de memória"],
	"lexicon": ["Words", "Mots", "Palabras", "Wörter", "Parole", "Palavras"],
	"settings": ["Settings", "Réglages", "Ajustes", "Einstellungen", "Impostazioni", "Ajustes"],
	"world": ["World", "Monde", "Mundo", "Welt", "Mondo", "Mundo"],
	"level": ["Level", "Niveau", "Nivel", "Level", "Livello", "Nível"],
	"boss": ["Boss grid", "Grille boss", "Gran reto", "Boss-Rätsel", "Griglia boss", "Grade chefe"],
	"locked": ["Finish the previous world to unlock", "Termine le monde précédent pour débloquer", "Termina el mundo anterior para desbloquear", "Beende die vorige Welt zum Freischalten", "Completa il mondo precedente per sbloccare", "Termine o mundo anterior para desbloquear"],
	"due": ["%d words to review", "%d mots à réviser", "%d palabras por repasar", "%d Wörter zu wiederholen", "%d parole da ripassare", "%d palavras para revisar"],
	"no_review": ["Nothing to review yet. Play a level first!", "Rien à réviser. Joue d'abord un niveau !", "Nada que repasar. ¡Juega un nivel primero!", "Noch nichts zu wiederholen. Spiel zuerst ein Level!", "Niente da ripassare. Gioca prima un livello!", "Nada para revisar. Jogue um nível primeiro!"],
	"across": ["Across", "Horizontal", "Horizontal", "Waagerecht", "Orizzontale", "Horizontal"],
	"down": ["Down", "Vertical", "Vertical", "Senkrecht", "Verticale", "Vertical"],
	"hint_letter": ["Letter", "Lettre", "Letra", "Buchstabe", "Lettera", "Letra"],
	"hint_word": ["Word", "Mot", "Palabra", "Wort", "Parola", "Palavra"],
	"hint_listen": ["Listen", "Écouter", "Escuchar", "Anhören", "Ascolta", "Ouvir"],
	"hint_shuffle": ["Letters", "Lettres", "Letras", "Buchstaben", "Lettere", "Letras"],
	"hint_example": ["Example", "Exemple", "Ejemplo", "Beispiel", "Esempio", "Exemplo"],
	"no_coins": ["Not enough coins", "Pas assez de pièces", "No tienes monedas", "Nicht genug Münzen", "Monete insufficienti", "Moedas insuficientes"],
	"perfect": ["Perfect!", "Parfait !", "¡Perfecto!", "Perfekt!", "Perfetto!", "Perfeito!"],
	"great": ["Great job!", "Bravo !", "¡Muy bien!", "Super gemacht!", "Ottimo lavoro!", "Muito bem!"],
	"good": ["Well done!", "Bien joué !", "¡Bien hecho!", "Gut gemacht!", "Ben fatto!", "Bom trabalho!"],
	"words_learned": ["Words in this grid", "Mots de cette grille", "Palabras de este crucigrama", "Wörter in diesem Rätsel", "Parole di questa griglia", "Palavras desta grade"],
	"time": ["Time", "Temps", "Tiempo", "Zeit", "Tempo", "Tempo"],
	"mistakes": ["Mistakes", "Erreurs", "Errores", "Fehler", "Errori", "Erros"],
	"hints": ["Hints", "Indices", "Pistas", "Hinweise", "Aiuti", "Dicas"],
	"next": ["Next", "Suivant", "Siguiente", "Weiter", "Avanti", "Próximo"],
	"home": ["Map", "Carte", "Mapa", "Karte", "Mappa", "Mapa"],
	"retry": ["Replay", "Rejouer", "Repetir", "Nochmal", "Rigioca", "Jogar de novo"],
	"back": ["Back", "Retour", "Atrás", "Zurück", "Indietro", "Voltar"],
	"sound": ["Sound effects", "Effets sonores", "Efectos de sonido", "Soundeffekte", "Effetti sonori", "Efeitos sonoros"],
	"voice": ["Pronunciation (voice)", "Prononciation (voix)", "Pronunciación (voz)", "Aussprache (Stimme)", "Pronuncia (voce)", "Pronúncia (voz)"],
	"haptics": ["Vibration", "Vibration", "Vibración", "Vibration", "Vibrazione", "Vibração"],
	"strict": ["Strict accents (É ≠ E)", "Accents stricts (É ≠ E)", "Acentos estrictos (É ≠ E)", "Strenge Akzente (Ä ≠ A)", "Accenti rigorosi (È ≠ E)", "Acentos estritos (É ≠ E)"],
	"online": ["Online extras (sentences, native audio)", "Bonus en ligne (phrases, audio natif)", "Extras en línea (frases, audio nativo)", "Online-Extras (Sätze, Muttersprachler-Audio)", "Extra online (frasi, audio nativo)", "Extras online (frases, áudio nativo)"],
	"language": ["Languages", "Langues", "Idiomas", "Sprachen", "Lingue", "Idiomas"],
	"reset": ["Reset progress", "Réinitialiser", "Reiniciar progreso", "Fortschritt löschen", "Azzera progressi", "Reiniciar progresso"],
	"reset_confirm": ["Tap again to erase everything", "Touche encore pour tout effacer", "Toca otra vez para borrar todo", "Nochmal tippen, um alles zu löschen", "Tocca di nuovo per cancellare tutto", "Toque de novo para apagar tudo"],
	"credits": ["Credits", "Crédits", "Créditos", "Credits", "Crediti", "Créditos"],
	"mastered": ["Mastered", "Maîtrisés", "Dominadas", "Gemeistert", "Padroneggiate", "Dominadas"],
	"learning": ["Learning", "En cours", "Aprendiendo", "Am Lernen", "In corso", "Aprendendo"],
	"empty_lexicon": ["Solve grids to collect words here.", "Résous des grilles pour collecter des mots.", "Resuelve crucigramas para coleccionar palabras.", "Löse Rätsel, um hier Wörter zu sammeln.", "Risolvi griglie per collezionare parole.", "Resolva grades para colecionar palavras."],
	"loading": ["Loading…", "Chargement…", "Cargando…", "Lädt…", "Caricamento…", "Carregando…"],
	"no_example": ["No example found", "Aucun exemple trouvé", "No hay ejemplo", "Kein Beispiel gefunden", "Nessun esempio", "Nenhum exemplo"],
	"streak": ["day streak", "jours de suite", "días seguidos", "Tage in Folge", "giorni di fila", "dias seguidos"],
	"xp": ["XP", "XP", "XP", "XP", "XP", "XP"],
	"reward": ["Reward", "Récompense", "Recompensa", "Belohnung", "Ricompensa", "Recompensa"],
	"new_world": ["New world unlocked!", "Nouveau monde débloqué !", "¡Nuevo mundo desbloqueado!", "Neue Welt freigeschaltet!", "Nuovo mondo sbloccato!", "Novo mundo desbloqueado!"],
}

var lang := "en"

func t(key: String) -> String:
	if not STRINGS.has(key):
		return key
	var row: Array = STRINGS[key]
	var i := LANGS.find(lang)
	if i < 0 or i >= row.size():
		i = 0
	return row[i]

func tf(key: String, value) -> String:
	return t(key) % value
