sentences = {
    1: [
        "1. Speakers don't always put everything that's important",
        "   to them into words."
    ],
    2: [
        "2. (Very often) you can understand a speaker's meaning",
        "   (by [observing their nonverbal behaviors])",
        "   such as a change (in a vocal tone or volume),",
        "   eye contact, facial expressions, and gestures)."
    ],
    3: [
        "3. (As it is easy [to misinterpret nonverbal behavior]),",
        "   effective listeners (verbally) confirm their interpretations",
        "   (of someone's nonverbal communication)."
    ],
    4: [
        "4. A question (as simple as \"Do your nods indicate a yes vote?\")",
        "   can make sure [that everyone is (on the same wavelength)]."
    ],
    5: [
        "5. (If, (as nonverbal research indicates), more than half",
        "   (of a speaker's meaning) is conveyed (nonverbally)),",
        "   we are missing a lot of important information",
        "   (if we fail [to \"listen\" (to nonverbal behavior)])."
    ],
    6: [
        "6. (Even) Freud suggested [that \"he (that has eyes [to see]",
        "   and ears [to hear]) may convince himself",
        "   [that no mortal can keep a secret]\"]."
    ],
    7: [
        "7. (If his lips are silent), he chatters (with his fingertips);",
        "   betrayal oozes out (of him) (at every pore).\""
    ],
    8: [
        "8. (No wonder) it is difficult (for most people)",
        "   [to conceal [what they mean and feel]]",
        "   (in a face-to-face group discussion)."
    ]
}

for s_idx, lines in sentences.items():
    print(f"=== S{s_idx} ===")
    for l_idx, line in enumerate(lines):
        print(f"L{l_idx}: {line}")
        ruler = "".join(str(i % 10) for i in range(len(line)))
        tens = "".join(str(i // 10) if i % 10 == 0 else " " for i in range(len(line)))
        print("    " + tens)
        print("    " + ruler)
