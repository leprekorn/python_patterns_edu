-- Debug queries

select * from batches;
select * from allocations;
select * from order_lines;


-- Manual cleaning
truncate table products CASCADE;
truncate table allocations CASCADE;
truncate table batches CASCADE;
truncate table order_lines CASCADE;
