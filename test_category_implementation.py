#!/usr/bin/env python3
"""
Test script to verify that the category implementation works correctly
"""

def test_imports():
    """Test that all the updated imports work"""
    try:
        from app.models.product import SecondHandProduct
        from app.schemas.second_hand_product import (
            SecondHandProductCreate, 
            SecondHandProductUpdate, 
            CategoryUpdateRequest,
            ProductCategory
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_model_fields():
    """Test that the model has the new category fields"""
    try:
        from app.models.product import SecondHandProduct
        
        # Check if the model has the new fields
        expected_fields = ['category_id', 'category_name']
        model_columns = [column.name for column in SecondHandProduct.__table__.columns]
        
        missing_fields = [field for field in expected_fields if field not in model_columns]
        
        if missing_fields:
            print(f"❌ Missing fields in model: {missing_fields}")
            return False
        
        print("✅ Model has all required category fields")
        print(f"   Available fields: {[col for col in model_columns if 'category' in col]}")
        return True
    except Exception as e:
        print(f"❌ Model field test failed: {e}")
        return False

def test_schema_fields():
    """Test that schemas have the new category fields"""
    try:
        from app.schemas.second_hand_product import (
            SecondHandProductCreate, 
            SecondHandProductUpdate,
            CategoryUpdateRequest
        )
        
        # Check SecondHandProductCreate schema
        create_schema = SecondHandProductCreate.schema()
        create_properties = create_schema.get('properties', {})
        
        if 'category_id' not in create_properties or 'category_name' not in create_properties:
            print("❌ SecondHandProductCreate missing category fields")
            return False
        
        # Check SecondHandProductUpdate schema
        update_schema = SecondHandProductUpdate.schema()
        update_properties = update_schema.get('properties', {})
        
        if 'category_id' not in update_properties or 'category_name' not in update_properties:
            print("❌ SecondHandProductUpdate missing category fields")
            return False
        
        # Check CategoryUpdateRequest schema
        category_schema = CategoryUpdateRequest.schema()
        category_properties = category_schema.get('properties', {})
        
        if 'category_id' not in category_properties:
            print("❌ CategoryUpdateRequest missing category_id field")
            return False
        
        print("✅ All schemas have required category fields")
        return True
    except Exception as e:
        print(f"❌ Schema field test failed: {e}")
        return False

def test_service_methods():
    """Test that service has the new methods"""
    try:
        from app.services.second_hand_product_service import SecondHandProductService
        
        # Check if the service has the new methods
        expected_methods = ['update_product_category', 'update_shopify_product']
        
        missing_methods = []
        for method in expected_methods:
            if not hasattr(SecondHandProductService, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing methods in service: {missing_methods}")
            return False
        
        print("✅ Service has all required category methods")
        return True
    except Exception as e:
        print(f"❌ Service method test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Category Implementation")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Model Fields Test", test_model_fields),
        ("Schema Fields Test", test_schema_fields),
        ("Service Methods Test", test_service_methods),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"   {test_name} failed!")
    
    print("\n" + "=" * 50)
    print(f"🏁 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Category implementation is ready.")
        print("\n📝 Next steps:")
        print("   1. Run database migration to add category fields")
        print("   2. Test the API endpoints:")
        print("      - GET /second-hand/categories (get available categories)")
        print("      - POST /second-hand/products (create with category)")
        print("      - PUT /second-hand/products/{id} (update with category)")
        print("      - PUT /second-hand/products/{id}/category (update category only)")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    main()
