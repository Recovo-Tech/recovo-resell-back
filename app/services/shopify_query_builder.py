# app/services/shopify_query_builder.py
"""GraphQL Query Builder for Shopify API queries"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class GraphQLField:
    """Represents a GraphQL field with optional arguments and subfields"""
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    subfields: List['GraphQLField'] = field(default_factory=list)
    alias: Optional[str] = None

    def to_string(self, indent: int = 0) -> str:
        """Convert field to GraphQL string representation"""
        indent_str = "  " * indent
        
        # Handle alias
        field_name = f"{self.alias}: {self.name}" if self.alias else self.name
        
        # Handle arguments
        if self.arguments:
            args = []
            for key, value in self.arguments.items():
                if isinstance(value, str):
                    # Check if it's a GraphQL variable (starts with $)
                    if value.startswith('$'):
                        args.append(f'{key}: {value}')
                    else:
                        args.append(f'{key}: "{value}"')
                elif isinstance(value, bool):
                    args.append(f'{key}: {str(value).lower()}')
                else:
                    args.append(f'{key}: {value}')
            field_name += f"({', '.join(args)})"
        
        # Handle subfields
        if self.subfields:
            subfield_strs = [field.to_string(indent + 1) for field in self.subfields]
            subfields_str = "\n".join(subfield_strs)
            return f"{indent_str}{field_name} {{\n{subfields_str}\n{indent_str}}}"
        else:
            return f"{indent_str}{field_name}"


class ShopifyQueryBuilder:
    """Builder for constructing Shopify GraphQL queries"""

    @staticmethod
    def create_query(
        operation_name: str,
        fields: List[GraphQLField],
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a complete GraphQL query"""
        
        # Build variable definitions
        var_definitions = ""
        if variables:
            var_defs = [f"${key}: {value}" for key, value in variables.items()]
            var_definitions = f"({', '.join(var_defs)})"
        
        # Build fields
        field_strs = [field.to_string(1) for field in fields]
        fields_str = "\n".join(field_strs)
        
        return f"""
query {operation_name}{var_definitions} {{
{fields_str}
}}
""".strip()

    @staticmethod
    def create_mutation(
        operation_name: str,
        fields: List[GraphQLField],
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a complete GraphQL mutation"""
        
        # Build variable definitions
        var_definitions = ""
        if variables:
            var_defs = [f"${key}: {value}" for key, value in variables.items()]
            var_definitions = f"({', '.join(var_defs)})"
        
        # Build fields
        field_strs = [field.to_string(1) for field in fields]
        fields_str = "\n".join(field_strs)
        
        return f"""
mutation {operation_name}{var_definitions} {{
{fields_str}
}}
""".strip()

    @staticmethod
    def product_fields(
        include_variants: bool = True,
        include_images: bool = True,
        include_collections: bool = False,
        variant_limit: int = 10,
        image_limit: int = 10
    ) -> List[GraphQLField]:
        """Standard product fields for queries"""
        fields = [
            GraphQLField("id"),
            GraphQLField("title"),
            GraphQLField("handle"),
            GraphQLField("description"),
            GraphQLField("descriptionHtml"),
            GraphQLField("status"),
            GraphQLField("productType"),
            GraphQLField("vendor"),
            GraphQLField("tags"),
            GraphQLField("createdAt"),
            GraphQLField("updatedAt"),
            GraphQLField("publishedAt"),
            GraphQLField(
                "options",
                subfields=[
                    GraphQLField("id"),
                    GraphQLField("name"),
                    GraphQLField("values")
                ]
            )
        ]

        if include_variants:
            fields.append(
                GraphQLField(
                    "variants",
                    arguments={"first": variant_limit},
                    subfields=[
                        GraphQLField(
                            "edges",
                            subfields=[
                                GraphQLField(
                                    "node",
                                    subfields=[
                                        GraphQLField("id"),
                                        GraphQLField("sku"),
                                        GraphQLField("barcode"),
                                        GraphQLField("title"),
                                        GraphQLField("price"),
                                        GraphQLField("compareAtPrice"),
                                        GraphQLField("weight"),
                                        GraphQLField("weightUnit"),
                                        GraphQLField("inventoryQuantity"),
                                        GraphQLField("availableForSale"),
                                        GraphQLField(
                                            "selectedOptions",
                                            subfields=[
                                                GraphQLField("name"),
                                                GraphQLField("value")
                                            ]
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            )

        if include_images:
            fields.append(
                GraphQLField(
                    "images",
                    arguments={"first": image_limit},
                    subfields=[
                        GraphQLField(
                            "edges",
                            subfields=[
                                GraphQLField(
                                    "node",
                                    subfields=[
                                        GraphQLField("id"),
                                        GraphQLField("url"),
                                        GraphQLField("altText"),
                                        GraphQLField("width"),
                                        GraphQLField("height")
                                    ]
                                )
                            ]
                        )
                    ]
                )
            )

        if include_collections:
            fields.append(
                GraphQLField(
                    "collections",
                    arguments={"first": 10},
                    subfields=[
                        GraphQLField(
                            "edges",
                            subfields=[
                                GraphQLField(
                                    "node",
                                    subfields=[
                                        GraphQLField("id"),
                                        GraphQLField("title"),
                                        GraphQLField("handle")
                                    ]
                                )
                            ]
                        )
                    ]
                )
            )

        return fields

    @staticmethod
    def collection_fields(include_products: bool = False, product_limit: int = 10) -> List[GraphQLField]:
        """Standard collection fields for queries"""
        fields = [
            GraphQLField("id"),
            GraphQLField("title"),
            GraphQLField("handle"),
            GraphQLField("description"),
            GraphQLField("descriptionHtml"),
            GraphQLField("updatedAt"),
            GraphQLField("sortOrder"),
            GraphQLField(
                "image",
                subfields=[
                    GraphQLField("id"),
                    GraphQLField("url"),
                    GraphQLField("altText")
                ]
            )
        ]

        if include_products:
            fields.append(
                GraphQLField(
                    "products",
                    arguments={"first": product_limit},
                    subfields=[
                        GraphQLField(
                            "edges",
                            subfields=[
                                GraphQLField(
                                    "node",
                                    subfields=ShopifyQueryBuilder.product_fields(
                                        include_variants=False,
                                        include_images=False
                                    )
                                )
                            ]
                        )
                    ]
                )
            )

        return fields

    @staticmethod
    def pagination_info() -> GraphQLField:
        """Standard pagination info field"""
        return GraphQLField(
            "pageInfo",
            subfields=[
                GraphQLField("hasNextPage"),
                GraphQLField("hasPreviousPage"),
                GraphQLField("startCursor"),
                GraphQLField("endCursor")
            ]
        )


class CommonQueries:
    """Pre-built common Shopify queries"""

    @staticmethod
    def get_product_by_id() -> str:
        """Query to get a product by ID"""
        fields = [
            GraphQLField(
                "product",
                arguments={"id": "$id"},
                subfields=ShopifyQueryBuilder.product_fields()
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "getProduct",
            fields,
            {"id": "ID!"}
        )

    @staticmethod
    def get_products_with_pagination() -> str:
        """Query to get products with pagination"""
        fields = [
            GraphQLField(
                "products",
                arguments={
                    "first": "$first",
                    "after": "$after",
                    "query": "$query"
                },
                subfields=[
                    GraphQLField(
                        "edges",
                        subfields=[
                            GraphQLField(
                                "node",
                                subfields=ShopifyQueryBuilder.product_fields()
                            ),
                            GraphQLField("cursor")
                        ]
                    ),
                    ShopifyQueryBuilder.pagination_info()
                ]
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "getProducts",
            fields,
            {
                "first": "Int!",
                "after": "String",
                "query": "String"
            }
        )

    @staticmethod
    def get_product_by_sku() -> str:
        """Query to get a product by SKU"""
        fields = [
            GraphQLField(
                "products",
                arguments={"first": 1, "query": "$query"},
                subfields=[
                    GraphQLField(
                        "edges",
                        subfields=[
                            GraphQLField(
                                "node",
                                subfields=ShopifyQueryBuilder.product_fields()
                            )
                        ]
                    )
                ]
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "getProductBySku",
            fields,
            {"query": "String!"}
        )

    @staticmethod
    def get_collections_with_pagination() -> str:
        """Query to get collections with pagination"""
        fields = [
            GraphQLField(
                "collections",
                arguments={
                    "first": "$first",
                    "after": "$after",
                    "query": "$query"
                },
                subfields=[
                    GraphQLField(
                        "edges",
                        subfields=[
                            GraphQLField(
                                "node",
                                subfields=ShopifyQueryBuilder.collection_fields()
                            ),
                            GraphQLField("cursor")
                        ]
                    ),
                    ShopifyQueryBuilder.pagination_info()
                ]
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "getCollections",
            fields,
            {
                "first": "Int!",
                "after": "String",
                "query": "String"
            }
        )

    @staticmethod
    def get_collection_by_id() -> str:
        """Query to get a collection by ID"""
        fields = [
            GraphQLField(
                "collection",
                arguments={"id": "$id"},
                subfields=ShopifyQueryBuilder.collection_fields(include_products=True)
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "getCollection",
            fields,
            {"id": "ID!"}
        )

    @staticmethod
    def create_product() -> str:
        """Mutation to create a product"""
        fields = [
            GraphQLField(
                "productCreate",
                arguments={"input": "$input"},
                subfields=[
                    GraphQLField(
                        "product",
                        subfields=ShopifyQueryBuilder.product_fields()
                    ),
                    GraphQLField(
                        "userErrors",
                        subfields=[
                            GraphQLField("field"),
                            GraphQLField("message")
                        ]
                    )
                ]
            )
        ]
        return ShopifyQueryBuilder.create_mutation(
            "createProduct",
            fields,
            {"input": "ProductInput!"}
        )

    @staticmethod
    def update_product() -> str:
        """Mutation to update a product"""
        fields = [
            GraphQLField(
                "productUpdate",
                arguments={"input": "$input"},
                subfields=[
                    GraphQLField(
                        "product",
                        subfields=ShopifyQueryBuilder.product_fields()
                    ),
                    GraphQLField(
                        "userErrors",
                        subfields=[
                            GraphQLField("field"),
                            GraphQLField("message")
                        ]
                    )
                ]
            )
        ]
        return ShopifyQueryBuilder.create_mutation(
            "updateProduct",
            fields,
            {"input": "ProductInput!"}
        )

    @staticmethod
    def get_products_count() -> str:
        """Query to get products count (simplified)"""
        fields = [
            GraphQLField(
                "products",
                arguments={"first": 1, "query": "$query"},
                subfields=[
                    GraphQLField(
                        "edges",
                        subfields=[
                            GraphQLField(
                                "node",
                                subfields=[GraphQLField("id")]
                            )
                        ]
                    )
                ]
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "getProductsCount",
            fields,
            {"query": "String"}
        )

    @staticmethod
    def get_products_for_filters() -> str:
        """Query to get products for filter extraction"""
        fields = [
            GraphQLField(
                "products",
                arguments={"first": "$first"},
                subfields=[
                    GraphQLField(
                        "edges",
                        subfields=[
                            GraphQLField(
                                "node",
                                subfields=[
                                    GraphQLField("productType"),
                                    GraphQLField("vendor"),
                                    GraphQLField("tags")
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "getProductsForFilters",
            fields,
            {"first": "Int!"}
        )

    @staticmethod
    def get_products_for_count() -> str:
        """Query to get products for counting with pagination"""
        fields = [
            GraphQLField(
                "products",
                arguments={
                    "first": "$first",
                    "after": "$after",
                    "query": "$query"
                },
                subfields=[
                    GraphQLField(
                        "edges",
                        subfields=[
                            GraphQLField(
                                "node",
                                subfields=[GraphQLField("id")]
                            )
                        ]
                    ),
                    ShopifyQueryBuilder.pagination_info()
                ]
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "getProductsForCount",
            fields,
            {
                "first": "Int!",
                "after": "String",
                "query": "String"
            }
        )

    @staticmethod
    def get_taxonomy() -> str:
        """Query to get Shopify's product taxonomy"""
        fields = [
            GraphQLField(
                "taxonomy",
                subfields=[
                    GraphQLField(
                        "categories",
                        arguments={"first": 250},
                        subfields=[
                            GraphQLField(
                                "nodes",
                                subfields=[
                                    GraphQLField("id"),
                                    GraphQLField("name"),
                                    GraphQLField("fullName"),
                                    GraphQLField("parentId"),
                                    GraphQLField("level"),
                                    GraphQLField("isLeaf"),
                                    GraphQLField("childrenIds")
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
        return ShopifyQueryBuilder.create_query("GetAllCategories", fields)

    @staticmethod
    def get_subcategories() -> str:
        """Query to get subcategories for a parent category"""
        fields = [
            GraphQLField(
                "taxonomy",
                subfields=[
                    GraphQLField(
                        "categories",
                        arguments={"first": 250, "childrenOf": "$parentId"},
                        subfields=[
                            GraphQLField(
                                "nodes",
                                subfields=[
                                    GraphQLField("id"),
                                    GraphQLField("name"),
                                    GraphQLField("fullName"),
                                    GraphQLField("parentId"),
                                    GraphQLField("level"),
                                    GraphQLField("isLeaf"),
                                    GraphQLField("childrenIds")
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "GetChildCategories",
            fields,
            {"parentId": "ID!"}
        )

    @staticmethod
    def get_collection_products() -> str:
        """Query to get products from a specific collection"""
        product_fields = ShopifyQueryBuilder.product_fields(
            include_variants=True,
            include_images=True,
            include_collections=True,
            image_limit=5
        )
        
        fields = [
            GraphQLField(
                "collection",
                arguments={"id": "$id"},
                subfields=[
                    GraphQLField("id"),
                    GraphQLField("title"),
                    GraphQLField("handle"),
                    GraphQLField(
                        "products",
                        arguments={"first": "$first", "after": "$after"},
                        subfields=[
                            GraphQLField(
                                "edges",
                                subfields=[
                                    GraphQLField("node", subfields=product_fields)
                                ]
                            ),
                            ShopifyQueryBuilder.pagination_info()
                        ]
                    )
                ]
            )
        ]
        return ShopifyQueryBuilder.create_query(
            "getCollectionProducts",
            fields,
            {
                "id": "ID!",
                "first": "Int!",
                "after": "String"
            }
        )
