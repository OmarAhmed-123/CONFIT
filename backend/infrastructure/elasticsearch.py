"""
CONFIT Backend - Elasticsearch Infrastructure
=============================================
Elasticsearch client for product search and analytics.
"""

import os
from typing import Any, Dict, List, Optional

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# ELASTICSEARCH CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def get_elasticsearch_url() -> str:
    """Get Elasticsearch URL."""
    return os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT
# ─────────────────────────────────────────────────────────────────────────────

es_client: Optional[AsyncElasticsearch] = None


async def get_elasticsearch_client() -> AsyncElasticsearch:
    """Get or create Elasticsearch client."""
    global es_client
    
    if es_client is None:
        es_client = AsyncElasticsearch(
            [get_elasticsearch_url()],
            verify_certs=False,
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
    
    return es_client


async def close_elasticsearch() -> None:
    """Close Elasticsearch connection."""
    global es_client
    if es_client:
        await es_client.close()
        es_client = None


# ─────────────────────────────────────────────────────────────────────────────
# INDICES
# ─────────────────────────────────────────────────────────────────────────────

PRODUCT_INDEX = "confit_products"
BRAND_INDEX = "confit_brands"
USER_INDEX = "confit_users"
WARDROBE_INDEX = "confit_wardrobe"
OUTFIT_INDEX = "confit_outfits"


PRODUCT_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "name": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {"type": "completion"}
                }
            },
            "slug": {"type": "keyword"},
            "description": {"type": "text", "analyzer": "standard"},
            "brand_id": {"type": "keyword"},
            "brand_name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "category_id": {"type": "keyword"},
            "category_name": {"type": "keyword"},
            "color": {"type": "keyword"},
            "color_hex": {"type": "keyword"},
            "material": {"type": "keyword"},
            "pattern": {"type": "keyword"},
            "style_tags": {"type": "keyword"},
            "occasion_tags": {"type": "keyword"},
            "season_tags": {"type": "keyword"},
            "base_price": {"type": "float"},
            "sale_price": {"type": "float"},
            "current_price": {"type": "float"},
            "currency": {"type": "keyword"},
            "status": {"type": "keyword"},
            "is_featured": {"type": "boolean"},
            "is_new_arrival": {"type": "boolean"},
            "is_bestseller": {"type": "boolean"},
            "is_on_sale": {"type": "boolean"},
            "rating_average": {"type": "float"},
            "review_count": {"type": "integer"},
            "view_count": {"type": "integer"},
            "purchase_count": {"type": "integer"},
            "primary_image_url": {"type": "keyword", "index": False},
            "images": {"type": "keyword", "index": False},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "published_at": {"type": "date"},
            "style_compatibility": {"type": "integer"},
            "attributes": {"type": "object", "enabled": False},
        }
    },
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "default": {
                    "type": "standard",
                    "stopwords": "_english_"
                }
            }
        }
    }
}


BRAND_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "slug": {"type": "keyword"},
            "description": {"type": "text"},
            "industry": {"type": "keyword"},
            "is_verified": {"type": "boolean"},
            "is_featured": {"type": "boolean"},
            "product_count": {"type": "integer"},
            "follower_count": {"type": "integer"},
            "rating_average": {"type": "float"},
            "logo_url": {"type": "keyword", "index": False},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
    }
}


WARDROBE_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "name": {"type": "text"},
            "category": {"type": "keyword"},
            "brand": {"type": "keyword"},
            "color": {"type": "keyword"},
            "color_hex": {"type": "keyword"},
            "style_tags": {"type": "keyword"},
            "occasion_tags": {"type": "keyword"},
            "image_url": {"type": "keyword", "index": False},
            "auto_tags": {"type": "keyword"},
            "is_active": {"type": "boolean"},
            "is_favorite": {"type": "boolean"},
            "created_at": {"type": "date"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class ElasticsearchService:
    """Elasticsearch search service."""
    
    def __init__(self, client: AsyncElasticsearch):
        self.client = client
    
    async def create_indices(self) -> None:
        """Create all indices."""
        indices = [
            (PRODUCT_INDEX, PRODUCT_MAPPING),
            (BRAND_INDEX, BRAND_MAPPING),
            (WARDROBE_INDEX, WARDROBE_MAPPING),
        ]
        
        for index_name, mapping in indices:
            if not await self.client.indices.exists(index=index_name):
                await self.client.indices.create(index=index_name, body=mapping)
    
    async def delete_indices(self) -> None:
        """Delete all indices."""
        for index in [PRODUCT_INDEX, BRAND_INDEX, WARDROBE_INDEX]:
            if await self.client.indices.exists(index=index):
                await self.client.indices.delete(index=index)
    
    # Product operations
    async def index_product(self, product: Dict[str, Any]) -> bool:
        """Index a single product."""
        try:
            await self.client.index(
                index=PRODUCT_INDEX,
                id=product["id"],
                document=product
            )
            return True
        except Exception:
            return False
    
    async def bulk_index_products(self, products: List[Dict[str, Any]]) -> tuple:
        """Bulk index products."""
        actions = [
            {
                "_index": PRODUCT_INDEX,
                "_id": product["id"],
                "_source": product
            }
            for product in products
        ]
        
        success, failed = await async_bulk(
            self.client,
            actions,
            raise_on_error=False
        )
        return success, failed
    
    async def delete_product(self, product_id: str) -> bool:
        """Delete product from index."""
        try:
            await self.client.delete(index=PRODUCT_INDEX, id=product_id)
            return True
        except Exception:
            return False
    
    async def search_products(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Search products with filters and pagination."""
        must = []
        
        # Text query
        if query:
            must.append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^2", "description", "brand_name", "category_name"],
                    "fuzziness": "AUTO"
                }
            })
        else:
            must.append({"match_all": {}})
        
        # Filters
        filter_clauses = []
        if filters:
            if filters.get("brand_id"):
                filter_clauses.append({"term": {"brand_id": filters["brand_id"]}})
            if filters.get("category_id"):
                filter_clauses.append({"term": {"category_id": filters["category_id"]}})
            if filters.get("color"):
                filter_clauses.append({"term": {"color": filters["color"]}})
            if filters.get("material"):
                filter_clauses.append({"term": {"material": filters["material"]}})
            if filters.get("style_tags"):
                filter_clauses.append({"terms": {"style_tags": filters["style_tags"]}})
            if filters.get("occasion_tags"):
                filter_clauses.append({"terms": {"occasion_tags": filters["occasion_tags"]}})
            if filters.get("season_tags"):
                filter_clauses.append({"terms": {"season_tags": filters["season_tags"]}})
            if filters.get("status"):
                filter_clauses.append({"term": {"status": filters["status"]}})
            if filters.get("is_featured"):
                filter_clauses.append({"term": {"is_featured": True}})
            if filters.get("is_new_arrival"):
                filter_clauses.append({"term": {"is_new_arrival": True}})
            if filters.get("is_bestseller"):
                filter_clauses.append({"term": {"is_bestseller": True}})
            if filters.get("is_on_sale"):
                filter_clauses.append({"term": {"is_on_sale": True}})
            if filters.get("price_min") is not None or filters.get("price_max") is not None:
                price_range = {}
                if filters.get("price_min") is not None:
                    price_range["gte"] = filters["price_min"]
                if filters.get("price_max") is not None:
                    price_range["lte"] = filters["price_max"]
                filter_clauses.append({"range": {"current_price": price_range}})
        
        body = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filter_clauses if filter_clauses else []
                }
            },
            "from": (page - 1) * page_size,
            "size": page_size,
        }
        
        if sort:
            body["sort"] = sort
        else:
            body["sort"] = [{"_score": {"order": "desc"}}]
        
        # Aggregations for filtering
        body["aggs"] = {
            "brands": {"terms": {"field": "brand_id", "size": 20}},
            "categories": {"terms": {"field": "category_id", "size": 20}},
            "colors": {"terms": {"field": "color", "size": 20}},
            "price_ranges": {
                "range": {
                    "field": "current_price",
                    "ranges": [
                        {"to": 50},
                        {"from": 50, "to": 100},
                        {"from": 100, "to": 200},
                        {"from": 200, "to": 500},
                        {"from": 500}
                    ]
                }
            }
        }
        
        return await self.client.search(index=PRODUCT_INDEX, body=body)
    
    async def suggest_products(self, prefix: str, size: int = 10) -> List[str]:
        """Get product name suggestions."""
        result = await self.client.search(
            index=PRODUCT_INDEX,
            body={
                "suggest": {
                    "product_suggest": {
                        "prefix": prefix,
                        "completion": {
                            "field": "name.suggest",
                            "size": size,
                            "skip_duplicates": True
                        }
                    }
                }
            }
        )
        
        suggestions = []
        for option in result.get("suggest", {}).get("product_suggest", [{}])[0].get("options", []):
            suggestions.append(option["_source"]["name"])
        
        return suggestions
    
    # Brand operations
    async def index_brand(self, brand: Dict[str, Any]) -> bool:
        """Index a single brand."""
        try:
            await self.client.index(
                index=BRAND_INDEX,
                id=brand["id"],
                document=brand
            )
            return True
        except Exception:
            return False
    
    async def search_brands(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Search brands."""
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name", "description", "industry"]
                }
            },
            "from": (page - 1) * page_size,
            "size": page_size,
        }
        
        return await self.client.search(index=BRAND_INDEX, body=body)
    
    # Wardrobe operations
    async def index_wardrobe_item(self, item: Dict[str, Any]) -> bool:
        """Index a wardrobe item."""
        try:
            await self.client.index(
                index=WARDROBE_INDEX,
                id=item["id"],
                document=item
            )
            return True
        except Exception:
            return False
    
    async def search_wardrobe(
        self,
        user_id: str,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Search user's wardrobe."""
        must = [{"term": {"user_id": user_id}}]
        
        if query:
            must.append({
                "multi_match": {
                    "query": query,
                    "fields": ["name", "brand", "category"]
                }
            })
        
        filter_clauses = []
        if filters:
            if filters.get("category"):
                filter_clauses.append({"term": {"category": filters["category"]}})
            if filters.get("color"):
                filter_clauses.append({"term": {"color": filters["color"]}})
            if filters.get("brand"):
                filter_clauses.append({"term": {"brand": filters["brand"]}})
            if filters.get("style_tags"):
                filter_clauses.append({"terms": {"style_tags": filters["style_tags"]}})
            if filters.get("is_favorite"):
                filter_clauses.append({"term": {"is_favorite": True}})
        
        body = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filter_clauses
                }
            },
            "from": (page - 1) * page_size,
            "size": page_size,
        }
        
        return await self.client.search(index=WARDROBE_INDEX, body=body)
    
    async def similar_products(
        self,
        product_id: str,
        size: int = 10
    ) -> Dict[str, Any]:
        """Find similar products using more_like_this."""
        return await self.client.search(
            index=PRODUCT_INDEX,
            body={
                "query": {
                    "more_like_this": {
                        "fields": ["name", "description", "style_tags", "color", "category_name"],
                        "like": [{"_index": PRODUCT_INDEX, "_id": product_id}],
                        "min_term_freq": 1,
                        "max_query_terms": 25,
                        "min_doc_freq": 1
                    }
                },
                "size": size
            }
        )
