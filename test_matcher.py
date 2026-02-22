
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class MockPerson:
    id: int
    name: str
    email: Optional[str] = None

class MockPersonController:
    def __init__(self, persons: List[MockPerson]):
        self.persons = persons
        self.created_count = 0
    
    def get_all(self):
        return self.persons
    
    def create_person(self, name: str, emails: List[str]):
        new_id = 999 + self.created_count
        self.created_count += 1
        return MockPerson(id=new_id, name=name, email=emails[0] if emails else None)

# Import actual PersonMatcher logic (mimicked here for self-contained test)
import re
import unicodedata
from thefuzz import fuzz, process

class PersonMatcherTest:
    def __init__(self, person_controller):
        self.person_controller = person_controller
        self._persons_cache = {}
        self._emails_cache = {}

    def preload_cache(self):
        all_persons = self.person_controller.get_all()
        for p in all_persons:
            name = p.name
            email = p.email
            if name: self._persons_cache[name] = p
            if email: self._emails_cache[email.lower()] = p

    def normalize_name(self, name: str) -> str:
        if not name: return ""
        name_str = name.lower()
        name_str = "".join(c for c in unicodedata.normalize("NFD", name_str) if unicodedata.category(c) != "Mn")
        name_str = re.sub(r"[^a-z\s]", " ", name_str)
        return " ".join(name_str.split())

    def match_or_create(self, name: str, email=None):
        normalized_input = self.normalize_name(name)
        # Check cache
        for cached_name, person in self._persons_cache.items():
            if self.normalize_name(cached_name) == normalized_input:
                return person
        # Create
        emails = [email] if email else []
        p = self.person_controller.create_person(name=name, emails=emails)
        self._persons_cache[name] = p
        return p

# Test Cases
ctrl = MockPersonController([
    MockPerson(7, 'Gustavo Maia De Almeida'),
    MockPerson(74, 'Gustavo Maia de Almeida')
])
matcher = PersonMatcherTest(ctrl)
matcher.preload_cache()

print(f"Cache keys: {list(matcher._persons_cache.keys())}")

# Try to match a new variant
target = 'Gustavo Maia De Almeida'
result = matcher.match_or_create(target)
print(f"Match for '{target}': ID {result.id}")

target2 = 'Gustavo Maia de Almeida'
result2 = matcher.match_or_create(target2)
print(f"Match for '{target2}': ID {result2.id}")
