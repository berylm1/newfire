from datetime import timedelta
from superlinked import framework as sl


class LegalDocument(sl.Schema):
    doc_id:       sl.IdField
    tenant_id:    sl.String
    title:        sl.String
    body_text:    sl.String
    jurisdiction: sl.String
    doc_type:     sl.String
    date_filed:   sl.Timestamp
    citation:     sl.String
    source_doc:   sl.String
    chunk_idx:    sl.Integer


legal_doc = LegalDocument()

text_space = sl.TextSimilaritySpace(
    text=legal_doc.body_text,
    model="BAAI/bge-m3",
)

recency_space = sl.RecencySpace(
    timestamp=legal_doc.date_filed,
    period_time_list=[
        sl.PeriodTime(timedelta(days=365),    weight=1.0),
        sl.PeriodTime(timedelta(days=365 * 3), weight=0.6),
        sl.PeriodTime(timedelta(days=365 * 10), weight=0.2),
    ],
    negative_filter=-0.5,
)

jurisdiction_space = sl.CategoricalSimilaritySpace(
    category_input=legal_doc.jurisdiction,
    categories=[
        "US-SCOTUS", "US-BIA", "US-AAO", "US-INA", "US-CFR",
        "US-1CIR", "US-2CIR", "US-3CIR", "US-4CIR", "US-5CIR",
        "US-6CIR", "US-7CIR", "US-8CIR", "US-9CIR", "US-10CIR",
        "US-11CIR", "US-DCCIR", "UK-UT-IAC", "CA-IRB", "OTHER",
    ],
    negative_filter=-0.2,
    uncategorized_as_category=True,
)

doc_type_space = sl.CategoricalSimilaritySpace(
    category_input=legal_doc.doc_type,
    categories=["statute", "regulation", "case", "memo", "brief", "policy"],
    negative_filter=0.0,
    uncategorized_as_category=False,
)

index = sl.Index(
    spaces=[text_space, recency_space, jurisdiction_space, doc_type_space],
    fields=[
        legal_doc.tenant_id,
        legal_doc.doc_type,
        legal_doc.jurisdiction,
        legal_doc.date_filed,
    ],
)

query = (
    sl.Query(
        index,
        weights={
            text_space:         sl.Param("w_text",    default=0.55),
            recency_space:      sl.Param("w_recency",  default=0.25),
            jurisdiction_space: sl.Param("w_jur",      default=0.12),
            doc_type_space:     sl.Param("w_type",     default=0.08),
        },
    )
    .find(legal_doc)
    .similar(text_space.text,              sl.Param("query_text"))
    .similar(jurisdiction_space.category,  sl.Param("pref_jurisdiction"))
    .similar(doc_type_space.category,      sl.Param("pref_doc_type"))
    .filter(legal_doc.tenant_id  == sl.Param("tenant_id"))
    .filter(legal_doc.date_filed >= sl.Param("date_after", default=0))
    .filter(legal_doc.jurisdiction == sl.Param("jur_eq",  default=None))
    .filter(legal_doc.doc_type     == sl.Param("type_eq", default=None))
    .limit(sl.Param("top_k", default=8))
    .select_all()
)
