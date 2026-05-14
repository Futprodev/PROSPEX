-- Run this in the Supabase SQL Editor once.
-- Defines the RPC function the RAG retriever uses to do pgvector cosine search.
--
-- The Supabase Python client cannot express pgvector's `<=>` operator,
-- so we wrap the similarity query in a SQL function and call it via .rpc().

create or replace function match_regulations(
    query_embedding vector(768),
    match_count     int
)
returns table (
    id          uuid,
    source      text,
    title       text,
    url         text,
    date        text,
    summary     text,
    full_text   text,
    similarity  float
)
language sql stable
as $$
    select
        r.id,
        r.source,
        r.title,
        r.url,
        r.date,
        r.summary,
        r.full_text,
        1 - (r.embedding <=> query_embedding) as similarity
    from regulation_updates r
    where r.embedding is not null
      and r.is_relevant = true
    order by r.embedding <=> query_embedding
    limit match_count;
$$;
