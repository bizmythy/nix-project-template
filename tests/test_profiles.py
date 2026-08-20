from nix_project_generator.profiles import Language, normalized_languages


def test_languages_are_deduplicated_in_stable_order() -> None:
    languages = normalized_languages(("typescript", "rust", "rust", "go"))

    assert languages == (Language.RUST, Language.GO, Language.TYPESCRIPT)
