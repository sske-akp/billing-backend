-- SQL script to insert sample data into the sskedata schema

-- Note: Using sskedata.uuid_generate_v4() for 'id' columns where applicable,
-- and regenerated UUIDs for foreign key references to avoid syntax errors.

-- Insert into product_brands
INSERT INTO sskedata.product_brands (id, brand, company, disabled) VALUES
(sskedata.uuid_generate_v4(), 'Havells', 'Havells India Ltd.', FALSE),
(sskedata.uuid_generate_v4(), 'Philips', 'Philips India Ltd.', FALSE),
(sskedata.uuid_generate_v4(), 'Crompton', 'Crompton Greaves Consumer Electricals Ltd.', FALSE);

-- Insert into product_categories
INSERT INTO sskedata.product_categories (id, name, disabled) VALUES
(sskedata.uuid_generate_v4(), 'Fans', FALSE),
(sskedata.uuid_generate_v4(), 'Bulbs', FALSE),
(sskedata.uuid_generate_v4(), 'Motors', FALSE),
(sskedata.uuid_generate_v4(), 'Wires', FALSE);

-- Insert into products
-- Using regenerated UUIDs for brand_id and category_id
INSERT INTO sskedata.products (id, item, hsncode, unit, brand_id, category_id, created_at, updated_at, disabled) VALUES
(sskedata.uuid_generate_v4(), 'Ceiling Fan 1200mm', '841451', 'PCS', '1a2b3c4d-5e6f-4789-abcd-ef1234567890', '4d5e6f7a-8b9c-4a12-def0-234567890123', NOW(), NOW(), FALSE),
(sskedata.uuid_generate_v4(), 'LED Bulb 9W Cool White', '853950', 'PCS', '2b3c4d5e-6f7a-4890-bcde-f12345678901', '5e6f7a8b-9c0d-4b23-ef12-345678901234', NOW(), NOW(), FALSE),
(sskedata.uuid_generate_v4(), 'Single Phase Motor 1HP', '850140', 'PCS', '3c4d5e6f-7a8b-4901-cdef-123456789012', '6f7a8b9c-0d1e-4c34-f123-456789012345', NOW(), NOW(), FALSE),
(sskedata.uuid_generate_v4(), 'PVC Insulated Wire 1.5 sq mm', '854449', 'MTR', '1a2b3c4d-5e6f-4789-abcd-ef1234567890', '7a8b9c0d-1e2f-4d45-1234-567890123456', NOW(), NOW(), FALSE);

-- Insert into customers
-- Using regenerated UUIDs for id
INSERT INTO sskedata.customers (id, name, address, gstin, phone_number, email, created_at, updated_at) VALUES
('8b9c0d1e-2f3a-4e56-2345-678901234567', 'ABC Electricals', '123 Main St, Anytown', '22AAAAA0000A1Z5', '9876543210', 'abc@example.com', NOW(), NOW()),
('9c0d1e2f-3a4b-4f67-3456-789012345678', 'XYZ Contractors', '456 Oak Ave, Othercity', '22BBBBB0000B1Z6', '0123456789', 'xyz@example.com', NOW(), NOW());

-- Insert into invoices
-- Using regenerated UUIDs for id and customer_id
INSERT INTO sskedata.invoices (id, invoice_number, customer_id, date, invoice_type, total_amount, created_at, updated_at) VALUES
('a0b1c2d3-4e5f-4078-4567-890123456789', 'INV-001', '8b9c0d1e-2f3a-4e56-2345-678901234567', '2025-06-01', 'Sales', 2500.00, NOW(), NOW()),
('b1c2d3e4-5f6a-4189-5678-901234567890', 'INV-002', '9c0d1e2f-3a4b-4f67-3456-789012345678', '2025-06-05', 'Sales', 1500.00, NOW(), NOW());

-- Insert into product_batches
-- Using regenerated UUIDs for id and product_id
INSERT INTO sskedata.product_batches (id, product_id, batch_code, purchase_price, quantity, remaining_qty, purchase_date, source_type, created_at, disabled, discount_value) VALUES
('c2d3e4f5-6a7b-4290-6789-012345678901', 'h8i9j0k1-2345-6789-0123-def123456789', 'FAN-B1', 1500.00, 10, 8, '2025-05-15', 'Purchase', NOW(), FALSE, 0.00),
('d3e4f5g6-7b8c-43a1-7890-123456789012', 'i9j0k1l2-3456-7890-1234-ef1234567890', 'BULB-B1', 50.00, 100, 90, '2025-05-20', 'Purchase', NOW(), FALSE, 0.00);

-- Insert into invoice_items
-- Using regenerated UUIDs for id, invoice_id, product_id, and batch_id
INSERT INTO sskedata.invoice_items (id, invoice_id, product_id, batch_id, quantity, selling_price, tax_percent, total_price, is_official) VALUES
('e4f5g6h7-8c9d-44b2-8901-234567890123', 'a0b1c2d3-4e5f-4078-4567-890123456789', 'h8i9j0k1-2345-6789-0123-def123456789', 'c2d3e4f5-6a7b-4290-6789-012345678901', 2, 1200.00, 18.00, 2832.00, TRUE), -- 2 * 1200 * 1.18 = 2832
('f5g6h7i8-9d0e-45c3-9012-345678901234', 'a0b1c2d3-4e5f-4078-4567-890123456789', 'i9j0k1l2-3456-7890-1234-ef1234567890', 'd3e4f5g6-7b8c-43a1-7890-123456789012', 10, 80.00, 12.00, 896.00, TRUE), -- 10 * 80 * 1.12 = 896
('g6h7i8j9-0e1f-46d4-0123-456789012345', 'b1c2d3e4-5f6a-4189-5678-901234567890', 'i9j0k1l2-3456-7890-1234-ef1234567890', 'd3e4f5g6-7b8c-43a1-7890-123456789012', 15, 75.00, 12.00, 1260.00, TRUE); -- 15 * 75 * 1.12 = 1260

-- Insert into discounts
-- Using regenerated UUIDs for id, product_id, and category_id
INSERT INTO sskedata.discounts (id, product_id, name, value, is_active, created_at, updated_at, category_id) VALUES
('h7i8j9k0-1f2a-47e5-1234-567890123456', 'h8i9j0k1-2345-6789-0123-def123456789', 'Fan Promo', 10.00, TRUE, NOW(), NOW(), NULL), -- 10% off Fan
('i8j9k0l1-2a3b-48f6-2345-678901234567', NULL, 'Bulb Bulk Discount', 5.00, TRUE, NOW(), NOW(), '5e6f7a8b-9c0d-4b23-ef12-345678901234'); -- 5% off Bulbs category

-- Insert into stock (Assuming simple data structure based on schema)
-- Note: The 'stock' table schema seems different from the other tables using UUIDs.
-- Assuming 'id' is a simple integer primary key.
INSERT INTO sskedata.stock (id, company, item, quantity, priceperunit, totalprice, lastupdatetimestamp) VALUES
(1, 'Havells India Ltd.', 'Ceiling Fan 1200mm', 8.0, 1500.0, 12000.0, NOW()),
(2, 'Philips India Ltd.', 'LED Bulb 9W Cool White', 90.0, 50.0, 4500.0, NOW());

-- Insert into stock_summary (Assuming simple data structure based on schema)
-- Note: The 'stock_summary' table schema also seems different, with integer primary key and text types.
-- Assuming 'id' is a simple integer primary key, possibly serial.
INSERT INTO sskedata.stock_summary (id, item, location, quantity, rate, value) VALUES
(1, 'Ceiling Fan 1200mm', 'Warehouse A', 8.0, 1500.0, 12000.0),
(2, 'LED Bulb 9W Cool White', 'Warehouse A', 90.0, 50.0, 4500.0);
