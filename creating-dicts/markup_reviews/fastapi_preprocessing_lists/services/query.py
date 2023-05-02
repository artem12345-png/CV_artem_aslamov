query = """
with
({progon_1}) as first_run_id_
,({progon_2}) as second_run_id_
, markup_reviews_sentiments_phrases as (
 select
  mr.counter,
  mr.text_id,
  mr.topic_name
  , groupArray(phrase) filter (where sentiment_label = 'POSITIVE') as pos_phrases
  , groupArray(phrase) filter (where sentiment_label = 'NEGATIVE') as neg_phrases
  , groupArray(phrase) filter (where sentiment_label = 'NEURTAL') as neut_phrases
  , any(mr.comment_text) as comment_text
  , any(mr.text_sentiment_label) as text_sentiment_label
 from markup_reviews mr
 array join phrases as phrase
 where 1=1
  and topic_name is not null
  and (1=0
   or mr.counter = first_run_id_
   or mr.counter = second_run_id_
  )
 group by 1, 2, 3, mr.counter, mr.text_id, mr.topic_name
)
--select * from markup_reviews_sentiments_phrases limit 100;
, compare_santiments_with_topics as (
 select
  mr.text_id,
  mr.topic_name
  , any(mr.comment_text) as comment_text
  , any(pos_phrases) filter (where mr.counter = first_run_id_) as first_run_pos_phrases
  , any(pos_phrases) filter (where mr.counter = second_run_id_) as second_run_pos_phrases
  , any(neg_phrases) filter (where mr.counter = first_run_id_) as first_run_neg_phrases
  , any(neg_phrases) filter (where mr.counter = second_run_id_) as second_run_neg_phrases
  , any(neut_phrases) filter (where mr.counter = first_run_id_) as first_run_neut_phrases
  , any(neut_phrases) filter (where mr.counter = second_run_id_) as second_run_neut_phrases
  , any(first_run_id_) as first_run_id
  , any(second_run_id_) as second_run_id
  , any(true) filter (where mr.counter = first_run_id_) as is_first_run
  , any(true) filter (where mr.counter = second_run_id_) as is_second_run
  , anyLast(mr.text_sentiment_label) filter (where mr.counter = first_run_id_) as first_run_text_sentiment_label
  , anyLast(mr.text_sentiment_label) filter (where mr.counter = second_run_id_) as second_run_text_sentiment_label
 from markup_reviews_sentiments_phrases mr
 where 1=1
  and topic_name is not null
  and (1=0
   or mr.counter = first_run_id_
   or mr.counter = second_run_id_
  )
 group by 1, 2, mr.text_id,
  mr.topic_name
)
--select * from compare_santiments_with_topics;
, intersection_text_set as (
 select
  text_id
 from compare_santiments_with_topics
 group by 1, text_id
 -- есть ответы в обоих прогонах
 having (sum(is_first_run) > 0 and sum(is_second_run) > 0)
)
--select * from intersection_text_set;
, changed_sentiments as (
 select
  text_id,
  topic_name,
  comment_text
  , is_first_run
  , is_second_run
  -- позитивные фразы
  , first_run_pos_phrases
  , second_run_pos_phrases
  -- негативные фразы
  , first_run_neg_phrases
  , second_run_neg_phrases
  -- нейтральные фразы
  , first_run_neut_phrases
  , second_run_neut_phrases
  --
  , first_run_text_sentiment_label
  , second_run_text_sentiment_label
 from compare_santiments_with_topics compare
 where 1=0
  or (1=1
   and (is_first_run and is_second_run)
   and text_id in (select text_id from intersection_text_set)
   and (1=0
    -- отличаются фразы
    or (arraySort(first_run_pos_phrases) <> arraySort(second_run_pos_phrases))
    or (arraySort(first_run_neg_phrases) <> arraySort(second_run_neg_phrases))
    or (arraySort(first_run_neut_phrases) <> arraySort(second_run_neut_phrases))
    -- отличаются сентименты
    or (first_run_text_sentiment_label <> second_run_text_sentiment_label)
   )
  )
  or (1=1
   -- нет темы в каком-то прогоне
   and text_id in (select text_id from intersection_text_set)
   and (not is_first_run or not is_second_run)
  )
)
select * from changed_sentiments limit 1000;
"""

get_run_info = """
select markup_version, counter_id, run_date, working_time, domain_id, topic_dictionary, ton_dictionary
reviews_count, nulls_phrases, neutral_overall, negative_overall, positive_overall
from markup_reviews_run_info mr
WHERE counter_id = {progon_1} or counter_id = {progon_2}
"""

get_second_part = """
select counter_id, SUM(nulls_phrases), SUM(negative_overall), SUM(positive_overall), SUM(neutral_overall) 
from markup_reviews_run_info mr
WHERE counter_id = {progon_1} or counter_id = {progon_2}
GROUP BY counter_id 
"""
total_reviews = """
select counter, COUNT(DISTINCT text_id) from markup_reviews
where counter = {progon_1} or counter = {progon_2}
GROUP by counter 
"""
meta_data = """
select DISTINCT counter_id, markup_version, topic_dictionary, ton_dictionary, domain_id, run_date from markup_reviews_run_info mrri 
WHERE counter_id = {progon_1} or counter_id = {progon_2}
limit 2
"""
sum_working_time = """
select  counter_id, sum(working_time)  from markup_reviews_run_info mrri 
WHERE counter_id = {progon_1} or counter_id = {progon_2}
GROUP BY counter_id 
"""