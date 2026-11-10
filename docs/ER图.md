# 实体关系

以下 Mermaid 源码可直接编辑。Order_Details 对应实际含空格表名 `Order Details`。图中展示各实体的标识与关键关联字段；完整字段见数据字典。

```mermaid
erDiagram
    Customers o|--o{ Orders : CustomerID
    Employees o|--o{ Orders : EmployeeID
    Shippers o|--o{ Orders : ShipVia
    Orders ||--o{ Order_Details : OrderID
    Products ||--o{ Order_Details : ProductID
    Categories o|--o{ Products : CategoryID
    Suppliers o|--o{ Products : SupplierID
    Employees o|--o{ Employees : ReportsTo
    Regions ||--o{ Territories : RegionID
    Employees ||--o{ EmployeeTerritories : EmployeeID
    Territories ||--o{ EmployeeTerritories : TerritoryID
    Customers ||--o{ CustomerCustomerDemo : CustomerID
    CustomerDemographics ||--o{ CustomerCustomerDemo : CustomerTypeID
    Orders ||--o| app_order_meta : order_id

    Customers {
        varchar CustomerID PK
        text CompanyName
        text ContactName
        text Country
    }
    Orders {
        bigint OrderID PK
        varchar CustomerID FK
        bigint EmployeeID FK
        text OrderDate
        text RequiredDate
        text ShippedDate
        bigint ShipVia FK
        decimal Freight
    }
    Order_Details {
        bigint OrderID PK,FK
        bigint ProductID PK,FK
        decimal UnitPrice
        bigint Quantity
        double Discount
    }
    Products {
        bigint ProductID PK
        text ProductName
        bigint CategoryID FK
        bigint SupplierID FK
        decimal UnitPrice
        bigint UnitsInStock
        bigint ReorderLevel
        text Discontinued
    }
    Categories {
        bigint CategoryID PK
        text CategoryName
        text Description
    }
    Suppliers {
        bigint SupplierID PK
        text CompanyName
        text ContactName
    }
    Employees {
        bigint EmployeeID PK
        text FirstName
        text LastName
        bigint ReportsTo FK
    }
    Shippers {
        bigint ShipperID PK
        text CompanyName
    }
    Regions {
        bigint RegionID PK
        text RegionDescription
    }
    Territories {
        varchar TerritoryID PK
        text TerritoryDescription
        bigint RegionID FK
    }
    EmployeeTerritories {
        bigint EmployeeID PK,FK
        varchar TerritoryID PK,FK
    }
    CustomerDemographics {
        varchar CustomerTypeID PK
        text CustomerDesc
    }
    CustomerCustomerDemo {
        varchar CustomerID PK,FK
        varchar CustomerTypeID PK,FK
    }
    admin_user {
        bigint id PK
        varchar username UK
        varchar password_hash
        timestamp created_at
    }
    app_order_meta {
        bigint order_id PK,FK
        varchar status
        timestamp created_at
        timestamp cancelled_at
    }
```

# 关系模式

核心关系为 Customers(CustomerID)、Orders(OrderID, CustomerID, EmployeeID, ShipVia)、Order Details(OrderID, ProductID)、Products(ProductID, CategoryID, SupplierID)、Categories(CategoryID)、Suppliers(SupplierID)、Employees(EmployeeID, ReportsTo)、Shippers(ShipperID)。

订单明细由 (OrderID, ProductID) 唯一标识；一笔订单中同一商品只出现一次。员工与地区、客户与客户类型通过复合主键的中间表实现多对多关系。可空外键允许原始数据中的未指定关联，前端新建订单要求明确选择客户、员工、物流公司。

`admin_user` 是独立管理员实体。`app_order_meta` 与 Orders 为零或一对一关系：无扩展记录表示原始历史订单；有记录表示本系统订单，通过 active/cancelled 管理取消状态。
