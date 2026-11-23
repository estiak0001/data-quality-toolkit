-- Sample "dirty" table the demo checks run against: a few null emails,
-- a handful of stale rows, enough volume for row-count baselining to mean
-- something after a few check runs.
create schema if not exists demo;

create table if not exists demo.orders (
    id serial primary key,
    customer_id int,
    email text,
    updated_at timestamptz not null
);

insert into demo.orders (customer_id, email, updated_at)
select
    gs,
    case when gs % 97 = 0 then null else 'customer' || gs || '@example.com' end,
    case when gs % 150 = 0 then now() - interval '3 days' else now() - (gs % 180) * interval '1 minute' end
from generate_series(1, 5000) as gs;
