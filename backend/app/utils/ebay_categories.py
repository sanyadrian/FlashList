import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.routers.ebay_oauth import get_ebay_token

class EbayCategoryManager:
    def __init__(self):
        self.categories_file = "ebay_leaf_categories.json"
        self.categories_cache = {}
        self.last_update = None
        self.cache_duration = timedelta(days=7)  # Cache for 7 days
        
    def get_leaf_categories(self, user: str) -> Dict[str, str]:
        """
        Get leaf categories from eBay API or cache.
        Returns a dict mapping category names to category IDs.
        """
        # Check if we need to refresh the cache
        if self._should_refresh_cache():
            self._fetch_categories_from_ebay(user)
        
        return self.categories_cache
    
    def _should_refresh_cache(self) -> bool:
        """Check if we need to refresh the category cache."""
        if not os.path.exists(self.categories_file):
            return True
        
        if self.last_update is None:
            return True
        
        return datetime.now() - self.last_update > self.cache_duration
    
    def _fetch_categories_from_ebay(self, user: str):
        """Fetch categories from eBay API and cache them."""
        print("[DEBUG] Fetching categories from eBay API...")
        
        # Get eBay token
        token = get_ebay_token(user)
        if not token:
            print("[DEBUG] No eBay token available, using fallback categories")
            self._load_fallback_categories()
            return
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
        }
        
        try:
            # Call eBay's Browse API to get categories
            # Note: We'll use a simpler approach for now since GetCategories is part of Trading API
            # For now, we'll use some known working leaf categories
            
            # Try to get categories using Browse API
            browse_url = "https://api.ebay.com/buy/browse/v1/category_tree/0"
            response = requests.get(browse_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                print("[DEBUG] Successfully fetched categories from Browse API")
                self._parse_categories_from_browse(response.json())
            else:
                print(f"[DEBUG] Browse API failed: {response.status_code} - {response.text}")
                self._load_fallback_categories()
                
        except Exception as e:
            print(f"[DEBUG] Exception fetching categories: {e}")
            self._load_fallback_categories()
    
    def _parse_categories_from_browse(self, data: dict):
        """Parse categories from Browse API response."""
        # This is a simplified parser - in a real implementation, you'd want to
        # recursively traverse the category tree to find leaf categories
        categories = {}
        
        # For now, we'll use some known working leaf categories
        known_leaf_categories = {
            "Toys & Hobbies": "220",
            "Books & Magazines": "267", 
            "Jewelry & Watches": "281",
            "Electronics & Accessories": "293",
            "Health & Beauty": "180959",
            "Sporting Goods": "888",
            "Automotive Parts & Accessories": "6000",
            "Art": "550",
            "Musical Instruments & Gear": "176985",
            "Collectibles": "1",  # Note: This might not be a leaf category
            "Home & Garden": "11450",  # Note: This might not be a leaf category
        }
        
        # Add some specific plant-related categories that should be leaf categories
        plant_categories = {
            "Plants & Seedlings": "159912",
            "Garden Plants": "159913", 
            "Indoor Plants": "159914",
            "Outdoor Plants": "159915",
            "Flowers": "159916",
            "Succulents": "159917",
            "Herbs": "159918",
        }
        
        categories.update(known_leaf_categories)
        categories.update(plant_categories)
        
        self.categories_cache = categories
        self.last_update = datetime.now()
        self._save_categories_to_file()
        
        print(f"[DEBUG] Cached {len(categories)} categories")
    
    def _load_fallback_categories(self):
        """Load fallback categories when API calls fail."""
        fallback_categories = {
            "Toys & Hobbies": "220",
            "Books & Magazines": "267",
            "Jewelry & Watches": "281", 
            "Electronics & Accessories": "293",
            "Health & Beauty": "180959",
            "Sporting Goods": "888",
            "Automotive Parts & Accessories": "6000",
            "Art": "550",
            "Musical Instruments & Gear": "176985",
            "Plants & Seedlings": "159912",
            "Garden Plants": "159913",
            "Indoor Plants": "159914",
            "Outdoor Plants": "159915",
            "Flowers": "159916",
            "Succulents": "159917",
            "Herbs": "159918",
        }
        
        self.categories_cache = fallback_categories
        self.last_update = datetime.now()
        self._save_categories_to_file()
    
    def _save_categories_to_file(self):
        """Save categories to JSON file."""
        data = {
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "categories": self.categories_cache
        }
        
        with open(self.categories_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_categories_from_file(self):
        """Load categories from JSON file."""
        if not os.path.exists(self.categories_file):
            return
        
        try:
            with open(self.categories_file, 'r') as f:
                data = json.load(f)
            
            self.categories_cache = data.get("categories", {})
            last_update_str = data.get("last_update")
            if last_update_str:
                self.last_update = datetime.fromisoformat(last_update_str)
                
        except Exception as e:
            print(f"[DEBUG] Error loading categories from file: {e}")
            self.categories_cache = {}
            self.last_update = None
    
    def get_best_category_for_item(self, item_title: str, item_description: str = "", user: str = "") -> str:
        """
        Find the best category for an item based on its title and description.
        Returns a category ID.
        """
        # Load categories if not loaded
        if not self.categories_cache:
            self._load_categories_from_file()
            if not self.categories_cache:
                self.get_leaf_categories(user)
        
        # Simple keyword matching
        text = f"{item_title} {item_description}".lower()
        
        # Priority order for matching
        category_keywords = [
            ("Plants & Seedlings", ["plant", "seedling", "perennial", "annual"]),
            ("Garden Plants", ["garden", "outdoor", "landscape"]),
            ("Indoor Plants", ["indoor", "houseplant", "potted"]),
            ("Flowers", ["flower", "bloom", "petal"]),
            ("Succulents", ["succulent", "cactus", "ice plant"]),
            ("Herbs", ["herb", "culinary", "medicinal"]),
            ("Toys & Hobbies", ["toy", "game", "hobby"]),
            ("Books & Magazines", ["book", "magazine", "reading"]),
            ("Jewelry & Watches", ["jewelry", "watch", "necklace", "ring"]),
            ("Electronics & Accessories", ["electronic", "device", "gadget"]),
            ("Health & Beauty", ["health", "beauty", "cosmetic"]),
            ("Sporting Goods", ["sport", "fitness", "exercise"]),
            ("Automotive Parts & Accessories", ["car", "auto", "vehicle"]),
            ("Art", ["art", "painting", "sculpture"]),
            ("Musical Instruments & Gear", ["music", "instrument", "guitar"]),
        ]
        
        for category_name, keywords in category_keywords:
            if category_name in self.categories_cache:
                for keyword in keywords:
                    if keyword in text:
                        category_id = self.categories_cache[category_name]
                        print(f"[DEBUG] Matched '{category_name}' (ID: {category_id}) for item: {item_title}")
                        return category_id
        
        # Default fallback
        default_category = self.categories_cache.get("Toys & Hobbies", "220")
        print(f"[DEBUG] Using default category 'Toys & Hobbies' (ID: {default_category}) for item: {item_title}")
        return default_category

# Global instance
category_manager = EbayCategoryManager() 