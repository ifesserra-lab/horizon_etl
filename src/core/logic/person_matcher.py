import re
import unicodedata
from typing import Dict, Optional

from eo_lib import Person, PersonController
from loguru import logger
from thefuzz import fuzz, process


class PersonMatcher:
    """
    Service responsible for matching incoming names with existing Person records.

    This class handles name normalization, fuzzy matching, and caching to ensure
    idempotency and efficiency when identifying or creating persons during ingestion.
    """

    def __init__(self, person_controller: PersonController):
        """
        Initializes the PersonMatcher.

        Args:
            person_controller (PersonController): Controller used to interact with Person records.
        """
        self.person_controller = person_controller
        self._persons_cache: Dict[str, Person] = {}
        self._emails_cache: Dict[str, Person] = {}

    def preload_cache(self):
        """
        Preloads the internal persons cache from the database.

        Fetches all persons and populates _persons_cache using their names
        and _emails_cache using their emails.
        """
        logger.info("Pre-loading persons cache...")
        try:
            all_persons = self.person_controller.get_all()
            self._persons_cache = {}
            self._emails_cache = {}
            for p in all_persons:
                if isinstance(p, dict):
                    name = p.get("name")
                    email = p.get("email")
                else:
                    name = getattr(p, "name", None)
                    email = getattr(p, "email", None)
                if name:
                    self._persons_cache[name] = p
                if email:
                    self._emails_cache[email.lower()] = p
            logger.info(f"Loaded {len(self._persons_cache)} persons and {len(self._emails_cache)} emails into cache")
        except Exception as e:
            logger.warning(f"Failed to preload persons cache: {e}")

    def normalize_name(self, name: str) -> str:
        """
        Normalizes a name for consistent comparison.

        Steps:
        1. Normalize Unicode (NFD) and remove accents.
        2. Replace special characters with spaces and convert to UPPERCASE.
        3. Trim and remove double spaces.

        Args:
            name (str): The raw name string to normalize.

        Returns:
            str: The normalized name string.
        """
        if not name:
            return ""
        # 1. Normalize Unicode (NFD) and remove accents
        name_str = "".join(
            c
            for c in unicodedata.normalize("NFD", name)
            if unicodedata.category(c) != "Mn"
        )

        # 2. Replace special characters with spaces and Uppercase
        name_str = re.sub(r"[^A-Z\s]", " ", name_str.upper())

        # 3. Trim and remove double spaces
        return " ".join(name_str.split())

    def match_or_create(
        self, name: str, email: Optional[str] = None, strict_match: bool = False
    ) -> Optional[Person]:
        """
        Finds a person by email or name.
        Uses normalization and (optionally) fuzzy matching for names.
        Creates a new Person if no match is found.

        Args:
            name (str): The name of the person to match or create.
            email (Optional[str]): The email of the person to match.
            strict_match (bool): If True, only exact normalized matches (score 100) are accepted for name.

        Returns:
            Optional[Person]: The matched or newly created Person object, or None if creation fails.
        """
        if not name or not name.strip():
            # If name is missing but email is provided, maybe we can find by email anyway?
            # User requirement says Student and Supervisor are people and we should use name OR email.
            if not email:
                return None

        # 1. Match by Email first (highest priority)
        if email:
            email_key = email.strip().lower()
            if email_key in self._emails_cache:
                logger.debug(f"Match found by email: {email_key}")
                return self._emails_cache[email_key]

        name = name.strip() if name else ""
        normalized_input = self.normalize_name(name)

        # 2. Exact Match in Cache (Normalized)
        for cached_name, person in self._persons_cache.items():
            norm_cached = self.normalize_name(cached_name)
            if norm_cached == normalized_input:
                self._persons_cache[name] = person
                if email:
                    self._emails_cache[email.strip().lower()] = person
                return person

        # 3. Fuzzy Matching in Cache
        names_in_cache = list(self._persons_cache.keys())
        if names_in_cache and normalized_input:
            normalized_to_original = {self.normalize_name(n): n for n in names_in_cache}
            normalized_list = list(normalized_to_original.keys())

            best_norm_match, score = process.extractOne(
                normalized_input, normalized_list, scorer=fuzz.token_sort_ratio
            )

            # Threshold of 90%
            if score >= 90:
                # If strict match is enabled, we only accept 100% score (same tokens)
                if strict_match and score < 100:
                    logger.debug(
                        f"Fuzzy match '{best_norm_match}' ignored due to strict matching policy (score: {score})"
                    )
                else:
                    original_name = normalized_to_original[best_norm_match]
                    logger.info(
                        f"Fuzzy match found: '{name}' matches '{original_name}' (score: {score})"
                    )
                    person = self._persons_cache[original_name]
                    self._persons_cache[name] = person
                    if email:
                        self._emails_cache[email.strip().lower()] = person
                    return person

        # 4. Create new person (if no match found)
        try:
            emails = [email] if email else []
            person = self.person_controller.create_person(name=name, emails=emails)
            self._persons_cache[name] = person
            if email:
                self._emails_cache[email.strip().lower()] = person
            logger.debug(f"Created person: {name} (emails: {emails})")
            return person
        except Exception as e:
            logger.warning(f"Failed to create person '{name}': {e}")
            return None
