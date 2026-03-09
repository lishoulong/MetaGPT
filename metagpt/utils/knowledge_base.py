from abc import ABC, abstractmethod
from typing import List, Dict, Any

class KnowledgeItem(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseKnowledgeBase(ABC, BaseModel):
    """Abstract base class for a knowledge base."""

    @abstractmethod
    async def add_knowledge(self, item: KnowledgeItem):
        """Adds a single knowledge item to the knowledge base."""
        pass

    @abstractmethod
    async def add_batch(self, items: List[KnowledgeItem]):
        """Adds multiple knowledge items to the knowledge base."""
        pass

    @abstractmethod
    async def query(self, query_text: str, top_k: int = 1) -> List[KnowledgeItem]:
        """Queries the knowledge base for relevant information."""
        pass

    @abstractmethod
    async def get_by_id(self, item_id: str) -> KnowledgeItem | None:
        """Retrieves a knowledge item by its ID."""
        pass

class SimpleKnowledgeBase(BaseKnowledgeBase):
    """A simple in-memory knowledge base for demonstration."""
    _store: Dict[str, KnowledgeItem] = Field(default_factory=dict)

    async def add_knowledge(self, item: KnowledgeItem):
        self._store[item.id] = item

    async def add_batch(self, items: List[KnowledgeItem]):
        for item in items:
            self._store[item.id] = item

    async def query(self, query_text: str, top_k: int = 1) -> List[KnowledgeItem]:
        # For simplicity, a basic keyword search
        results = []
        for item in self._store.values():
            if query_text.lower() in item.content.lower():
                results.append(item)
        return results[:top_k]

    async def get_by_id(self, item_id: str) -> KnowledgeItem | None:
        return self._store.get(item_id)

# Example Usage:
# kb = SimpleKnowledgeBase()
# await kb.add_knowledge(KnowledgeItem(id="doc1", content="MetaGPT is a multi-agent framework."))
# results = await kb.query("What is MetaGPT?")
# print(results)
