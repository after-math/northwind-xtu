-- Run once after the complete source import. Re-running this file preserves data.
-- MySQL 8.0.16+, no routines or SUPER privilege required.
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS admin_user (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS app_order_meta (
  order_id BIGINT NOT NULL PRIMARY KEY,
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cancelled_at TIMESTAMP NULL,
  CONSTRAINT fk_app_order FOREIGN KEY (order_id) REFERENCES Orders(OrderID),
  CONSTRAINT ck_app_status CHECK (status IN ('active','cancelled')),
  CONSTRAINT ck_app_cancel_time CHECK (
    (status='active' AND cancelled_at IS NULL) OR
    (status='cancelled' AND cancelled_at IS NOT NULL)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- The source uses TEXT for OrderDate and ProductName, so prefix indexes are required.
-- Any existing index whose first column covers this prefix is reused.
SET @ddl = IF(EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='Orders' AND column_name='OrderDate' AND seq_in_index=1 AND (sub_part IS NULL OR sub_part>=10)), 'SELECT 1', 'CREATE INDEX idx_orders_date ON Orders (OrderDate(10))');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
SET @ddl = IF(EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='Orders' AND column_name='CustomerID' AND seq_in_index=1), 'SELECT 1', 'CREATE INDEX idx_orders_customer ON Orders (CustomerID)');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
SET @ddl = IF(EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='Products' AND column_name='ProductName' AND seq_in_index=1 AND (sub_part IS NULL OR sub_part>=120)), 'SELECT 1', 'CREATE INDEX idx_products_name ON Products (ProductName(120))');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
SET @ddl = IF(EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='Products' AND column_name='CategoryID' AND seq_in_index=1), 'SELECT 1', 'CREATE INDEX idx_products_category ON Products (CategoryID)');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Discount is DOUBLE in the source. Cast to six decimal places to avoid binary
-- floating artifacts in money expressions without rewriting any historical values.
CREATE OR REPLACE SQL SECURITY INVOKER VIEW v_order_amounts AS
SELECT o.OrderID, o.CustomerID, o.OrderDate, o.Freight,
       COALESCE(SUM(d.UnitPrice*d.Quantity*(1-CAST(d.Discount AS DECIMAL(10,6)))),0) AS SalesAmount
FROM Orders o
LEFT JOIN `Order Details` d ON d.OrderID=o.OrderID
LEFT JOIN app_order_meta m ON m.order_id=o.OrderID
WHERE m.order_id IS NULL OR m.status='active'
GROUP BY o.OrderID,o.CustomerID,o.OrderDate,o.Freight;

CREATE OR REPLACE SQL SECURITY INVOKER VIEW v_product_sales AS
SELECT p.ProductID,p.ProductName,p.CategoryID,
       COALESCE(SUM(CASE WHEN m.status='cancelled' THEN 0 ELSE d.Quantity END),0) AS TotalQuantity,
       COALESCE(SUM(CASE WHEN m.status='cancelled' THEN 0 ELSE d.UnitPrice*d.Quantity*(1-CAST(d.Discount AS DECIMAL(10,6))) END),0) AS SalesAmount
FROM Products p
LEFT JOIN `Order Details` d ON d.ProductID=p.ProductID
LEFT JOIN app_order_meta m ON m.order_id=d.OrderID
GROUP BY p.ProductID,p.ProductName,p.CategoryID;
