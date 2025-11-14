import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from bson import ObjectId

from schemas import Product, Order
from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class JSONEncoder:
    @staticmethod
    def encode_document(doc: dict):
        if not isinstance(doc, dict):
            return doc
        result = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                result[k] = str(v)
            else:
                result[k] = v
        return result


def seed_products_if_empty():
    if db is None:
        return
    count = db["product"].count_documents({})
    if count == 0:
        demo_products = [
            {
                "title": "Stride Pro Running Shoes",
                "description": "Lightweight, responsive cushioning for everyday runs.",
                "price": 129.99,
                "category": "running",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1200&auto=format&fit=crop",
                "color": "Black/White",
            },
            {
                "title": "AirFlex Lifestyle Sneakers",
                "description": "All-day comfort with a clean, versatile look.",
                "price": 109.0,
                "category": "lifestyle",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1542291026-94f2f98d1241?q=80&w=1200&auto=format&fit=crop",
                "color": "Sail/Volt",
            },
            {
                "title": "CourtMaster Basketball Shoes",
                "description": "Supportive fit with explosive traction on court.",
                "price": 149.5,
                "category": "basketball",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1542291026-cc1b8e1b1a1b?q=80&w=1200&auto=format&fit=crop",
                "color": "University Red",
            },
            {
                "title": "TrailX Terra",
                "description": "Grip-first design for mixed and rugged terrain.",
                "price": 139.0,
                "category": "trail",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1542291026-a58f8f5ccbfd?q=80&w=1200&auto=format&fit=crop",
                "color": "Olive/Black",
            },
        ]
        for p in demo_products:
            db["product"].insert_one(p)


@app.on_event("startup")
async def on_startup():
    try:
        seed_products_if_empty()
    except Exception:
        pass


@app.get("/")
def read_root():
    return {"message": "Ecommerce Backend Running"}


@app.get("/api/products")
def list_products(category: Optional[str] = None) -> JSONResponse:
    try:
        flt = {"category": category} if category else {}
        docs = list(db["product"].find(flt)) if db else []
        docs = [JSONEncoder.encode_document(d) for d in docs]
        return JSONResponse(docs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/orders")
def create_order(order: Order):
    try:
        # If total not provided or is 0, compute from product prices
        if (order.total is None) or order.total == 0:
            computed_total = 0.0
            # Build lookup map of product prices
            product_ids = [it.product_id for it in order.items]
            prod_docs = list(db["product"].find({"_id": {"$in": [ObjectId(pid) for pid in product_ids if ObjectId.is_valid(pid)]}})) if db else []
            price_map = {str(p["_id"]): float(p.get("price", 0)) for p in prod_docs}
            for it in order.items:
                computed_total += float(price_map.get(it.product_id, 0)) * it.quantity
            order.total = round(computed_total, 2)
        oid = create_document("order", order)
        return {"id": oid, "status": "created", "total": order.total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
