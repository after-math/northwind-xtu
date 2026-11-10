-- MySQL 8.0 · use northwind after importing data and extensions.sql.
-- Query examples use the ACTUAL 2016–2018 source dates; cancelled orders are excluded by views.
SET NAMES utf8mb4;

-- 1. SELECT: 商品目录
SELECT ProductID,ProductName,UnitPrice,UnitsInStock FROM Products;

-- 2. WHERE: 在售且库存不足的商品
SELECT ProductID,ProductName,UnitsInStock,ReorderLevel
FROM Products WHERE Discontinued='0' AND UnitsInStock<=ReorderLevel;

-- 3. LIKE: 按商品名模糊搜索
SELECT ProductID,ProductName FROM Products WHERE ProductName LIKE '%Ch%';

-- 4. ORDER BY: 单价从高到低排列
SELECT ProductID,ProductName,UnitPrice FROM Products ORDER BY UnitPrice DESC LIMIT 10;

-- 5. INNER JOIN: 含客户名称的订单销售额
SELECT v.OrderID,c.CompanyName,v.OrderDate,v.SalesAmount
FROM v_order_amounts v INNER JOIN Customers c ON c.CustomerID=v.CustomerID
ORDER BY v.OrderID DESC LIMIT 20;

-- 6. LEFT JOIN: 客户及其有效订单数，包括未成交客户
SELECT c.CustomerID,c.CompanyName,COUNT(v.OrderID) AS OrderCount
FROM Customers c LEFT JOIN v_order_amounts v ON v.CustomerID=c.CustomerID
GROUP BY c.CustomerID,c.CompanyName ORDER BY OrderCount DESC;

-- 7. GROUP BY: 按月统计销售额，保留全部数据年份
SELECT LEFT(OrderDate,7) AS SalesMonth,SUM(SalesAmount) AS Revenue
FROM v_order_amounts GROUP BY LEFT(OrderDate,7) ORDER BY SalesMonth;

-- 8. HAVING: 有效消费超过 30,000 的客户
SELECT c.CustomerID,c.CompanyName,SUM(v.SalesAmount) AS Spending
FROM Customers c JOIN v_order_amounts v ON v.CustomerID=c.CustomerID
GROUP BY c.CustomerID,c.CompanyName HAVING Spending>30000 ORDER BY Spending DESC;

-- 9. 子查询: 单价高于在售商品平均价格的商品
SELECT ProductName,UnitPrice FROM Products
WHERE Discontinued='0' AND UnitPrice>(SELECT AVG(UnitPrice) FROM Products WHERE Discontinued='0')
ORDER BY UnitPrice DESC;

-- 10. NOT EXISTS: 没有订单记录的客户
SELECT c.CustomerID,c.CompanyName FROM Customers c
WHERE NOT EXISTS (SELECT 1 FROM Orders o WHERE o.CustomerID=c.CustomerID);

-- 11. 视图查询: 排除取消订单的热销商品
SELECT ProductID,ProductName,TotalQuantity,SalesAmount
FROM v_product_sales ORDER BY SalesAmount DESC LIMIT 10;

-- 12. 多表连接: 分类销售统计
SELECT c.CategoryID,c.CategoryName,SUM(v.TotalQuantity) AS Quantity,SUM(v.SalesAmount) AS Revenue
FROM Categories c JOIN Products p ON p.CategoryID=c.CategoryID
JOIN v_product_sales v ON v.ProductID=p.ProductID
GROUP BY c.CategoryID,c.CategoryName ORDER BY Revenue DESC;

-- 13. INSERT / UPDATE / DELETE: 仅操作本事务新增的演示商品
-- AUTO_INCREMENT 序列允许留下间隙；回滚不会回退计数器，这是正常行为。
START TRANSACTION;
INSERT INTO Products (ProductName,CategoryID,SupplierID,UnitPrice,UnitsInStock,Discontinued)
VALUES ('课程演示商品（事务回滚）',1,1,9.90,5,'0');
SET @demo_product_id=LAST_INSERT_ID();
SELECT * FROM Products WHERE ProductID=@demo_product_id;
UPDATE Products SET UnitPrice=10.50 WHERE ProductID=@demo_product_id;
SELECT ProductID,ProductName,UnitPrice FROM Products WHERE ProductID=@demo_product_id;
DELETE FROM Products WHERE ProductID=@demo_product_id;
ROLLBACK;

-- 14. EXPLAIN: 实际文本日期的范围查询与函数查询
EXPLAIN SELECT OrderID,OrderDate FROM Orders WHERE OrderDate>='2018-04-01' AND OrderDate<'2018-05-01';
EXPLAIN SELECT OrderID,OrderDate FROM Orders WHERE LEFT(OrderDate,7)='2018-04';

-- 15. EXPLAIN: 外键索引过滤、名称前缀与包含搜索
EXPLAIN SELECT ProductID,ProductName FROM Products WHERE CategoryID=1;
EXPLAIN SELECT ProductID,ProductName FROM Products WHERE ProductName LIKE 'Ch%';
EXPLAIN SELECT ProductID,ProductName FROM Products WHERE ProductName LIKE '%Ch%';
