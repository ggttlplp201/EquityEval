"""Human D5d content dispositions, bound to reviewed immutable exhibit editions.

These are source-review assertions, not eligibility flags or normalized facts.
"""

from typing import Any

# Keyed by exact SEC exhibit filename; scope is explicit for lengthy legal documents.
REVIEWS: dict[str, dict[str, Any]] = {
    "dp229888_ex0301.htm": {
        "sha256": "c869078eaee96dfc845681a3be5f529d183b6efa2288b4bc0aa606be53171020",
        "scope": (
            "Preamble; Articles 1–3; selected Article 4 capital-stock passages; Articles 5–9 "
            "governance. Bounded accounting relevance review, not a legal-rights "
            "opinion."
        ),
        "relevance": "Share-class reclassification and governing-document restatement",
        "finding": (
            "Restated describes the certificate; reclassification converts Old "
            "Stock into Class A and founder holdings into Class B. These passages "
            "do not reclassify revenue or operating income. Capital actions require"
            " separate per-share review."
        ),
        "quotes": [
            (
                "This amended and restated certificate of incorporation, which "
                "restates, integrates, and amends the provisions of the certificate of "
                "incorporation"
            ),
            (
                "shall automatically be reclassified and become as one validly issued, "
                "fully paid, and non-assessable share of Class A Common Stock"
            ),
        ],
        "limit": (
            "No financial statements or affected-income-line reconciliation is "
            "established by these governance provisions."
        ),
    },
    "dp229888_ex0302.htm": {
        "sha256": "ffe9e463cbadf3165c67aaf5c5669bcb17d45062005dad8664e8f9c882208a81",
        "scope": (
            "Governance structure; books/officers provisions; Article VII including"
            " fiscal-year rule. Bounded accounting relevance review."
        ),
        "relevance": "Fiscal-calendar corroboration and governance",
        "finding": (
            "The fiscal-year provision corroborates the annual January–December "
            "period. Governance rules do not establish unchanged reported operands "
            "or auditor assurance."
        ),
        "quotes": [
            (
                "The fiscal year of the Corporation shall commence on January 1 and end"
                " on December 31 of each year."
            )
        ],
        "limit": "Fiscal-calendar corroboration is not financial-history or restatement clearance.",
    },
    "a20250722-selipskypressrel.htm": {
        "sha256": "51ed266fa58c4eb68446be9d6724e26878eba1d90e8532ec25bdb7ef0df143f4",
        "scope": "Entire director appointment announcement.",
        "relevance": "Governance appointment",
        "finding": (
            "Announcement describes Adam Selipsky joining the board and his "
            "professional experience. No FY2025 reported-line correction or "
            "financial-statement non-reliance declaration was identified in this "
            "body."
        ),
        "quotes": ["Adam Selipsky"],
        "limit": (
            "An appointment announcement cannot prove completeness of financial event history."
        ),
    },
    "pressrelease_finalxkirkk.htm": {
        "sha256": "828c0a3e96b4faaa85912c0da14f4957a3f00f6d35c9598a1a6a59b5d7e97db8",
        "scope": "Entire director appointment announcement.",
        "relevance": "Governance appointment",
        "finding": (
            "Announcement describes Kirk Koenigsbauer joining the board and "
            "Compensation and Risk Committees. No FY2025 reported-line correction "
            "or financial-statement non-reliance declaration was identified in this"
            " body."
        ),
        "quotes": ["Kirk Koenigsbauer"],
        "limit": (
            "An appointment announcement cannot prove completeness of financial event history."
        ),
    },
    "final-projecttaurusxshar.htm": {
        "sha256": "3228613d18804ae7f68a38f2eee17de2f656abffc9f298aad14096e353aab416",
        "scope": (
            "Preamble/party definitions, Section 3.12, Sections 4.6–4.8 and Article"
            " V. Scoped accounting review of the retained agreement; not exhaustive"
            " legal diligence or review of omitted schedules."
        ),
        "relevance": "Target financial representations and contractual reliance",
        "finding": (
            "Company means Tazapay; Circle is Guarantor. Section 4.6 represents "
            "target statements under SFRS with a March year-end, not Circle FY2025 "
            "GAAP operands. Section 3.12 limits seller contractual reliance; it is "
            "not a declaration that Circle financial statements should no longer be"
            " relied upon. Negotiated, disclosure-qualified representations are not"
            " audited source statements."
        ),
        "quotes": [
            (
                "Tazapay Pte. Ltd., a private company incorporated under the laws of "
                "Singapore (the “Company”)"
            ),
            (
                "Circle Internet Group, Inc., a Delaware corporation and indirect owner"
                " of Purchaser (the “Guarantor”)"
            ),
            "Singapore Financial Reporting Standards (“SFRS”)",
            "Section 3.12. No Reliance. Such Seller is a sophisticated party",
        ],
        "limit": (
            "Referenced target financial statements and confidential disclosure "
            "schedules are not supplied as audited evidence here. Their contents "
            "and any effects on later Circle accounting remain unconfirmed. This "
            "review cannot certify the whole transaction or clear Circle history."
        ),
    },
    "final_sept82026announcem.htm": {
        "sha256": "930c656e13e83dbcace46d2e24896bcf069e17db853eab77fa49b16e1621acd7",
        "scope": "Entire acquisition announcement, including forward-looking statements.",
        "relevance": "Proposed later acquisition; prospective accounting scope",
        "finding": (
            "The announcement describes a proposed Tazapay acquisition expected to "
            "close later, subject to conditions. It does not establish completed "
            "FY2025 consolidation or restate the selected annual operands."
        ),
        "quotes": [
            (
                "The deal is expected to close in 2027, subject to customary closing "
                "conditions and receipt of regulatory approvals"
            )
        ],
        "limit": (
            "Expected closing is not an actual closing or purchase-accounting "
            "result. Later accounting requires its own evidence."
        ),
    },
}

EARNINGS = {
    "q22025epr.htm": (
        "b210eb93ebbc8a8b7b2de38e6f838031c2ae50a4347906f45f349046a6295770",
        (
            "(unaudited) (in $ thousands, except per share information) Three "
            "Months Ended Six Months Ended June 30, 2025 June 30, 2024 June 30, "
            "2025 June 30, 2024"
        ),
        ["658,078", "430,030", "1,236,651", "795,124"],
        ["(325,582)", "50,246", "(232,642)", "102,565"],
        "0001628280-25-039781",
        [(0, "2025-04-01", "2025-06-30"), (2, "2025-01-01", "2025-06-30")],
    ),
    "nolivelinksversion_q3202.htm": (
        "67694609778ac36526f911335d130dcc80cef4a6398452527328369c7aa6e879",
        (
            "(unaudited) (in thousands, except per share information) Three Months "
            "Ended Nine Months Ended September 30, 2025 September 30, 2024 "
            "September 30, 2025 September 30, 2024"
        ),
        ["739,759", "445,762", "1,976,410", "1,240,886"],
        ["81,020", "63,799", "(151,622)", "166,364"],
        "0001876042-25-000047",
        [(0, "2025-07-01", "2025-09-30"), (2, "2025-01-01", "2025-09-30")],
    ),
    "final_circlereportsfourt.htm": (
        "2117035fd24456c42fbeaef628a6e5a344fc5b8c35b9da6d2ad8d48aa2b3d2bc",
        (
            "(in thousands, except per share information) Three Months Ended Year "
            "Ended (unaudited) December 31, 2025 December 31, 2024 December 31, "
            "2025 December 31, 2024"
        ),
        ["770,232", "435,367", "2,746,642", "1,676,253"],
        ["55,187", "794", "(96,435)", "167,158"],
        "0001876042-26-000062",
        [(2, "2025-01-01", "2025-12-31")],
    ),
    "final_05x11q1epr30.htm": (
        "c8ba42c8cffdd5726a4c195f86e0048d6700fb1dddade3f51472e7706a9c07c1",
        (
            "(unaudited) (in $ thousands, except per share information) Three "
            "Months Ended March 31, 2026 March 31, 2025"
        ),
        ["694,133", "578,573"],
        ["45,002", "92,940"],
        "0001876042-26-000150",
        [(0, "2026-01-01", "2026-03-31"), (1, "2025-01-01", "2025-03-31")],
    ),
    "augustepr-circle_q22026f.htm": (
        "126ed09433860b6c1b4a8d9f9686f86bcf219c08ea30e84410f562ccf2ed2f90",
        (
            "(unaudited) (in $ thousands, except per share information) Three "
            "Months Ended Six Months Ended June 30, 2026 June 30, 2025 June 30, "
            "2026 June 30, 2025"
        ),
        ["701,315", "658,078", "1,395,448", "1,236,651"],
        ["34,359", "(325,582)", "79,361", "(232,642)"],
        "0001876042-26-000248",
        [
            (0, "2026-04-01", "2026-06-30"),
            (1, "2025-04-01", "2025-06-30"),
            (2, "2026-01-01", "2026-06-30"),
            (3, "2025-01-01", "2025-06-30"),
        ],
    ),
}

for filename, earnings in EARNINGS.items():
    REVIEWS[filename] = {
        "sha256": earnings[0],
        "scope": (
            "Entire earnings release, consolidated statements and non-GAAP "
            "reconciliation/definition sections. Exact reported-row checks and "
            "independently retained periodic statement comparison below."
        ),
        "relevance": "Direct reported operating-statement corroboration",
        "finding": (
            "Selected reported rows agree with the paired periodic statement for "
            "the explicitly tested periods. No reported-line restatement or "
            "financial-statement non-reliance declaration was identified in this "
            "release. Non-GAAP measures remain separate from the reported operating"
            " result."
        ),
        "quotes": ["CONSOLIDATED STATEMENTS OF OPERATIONS"],
        "limit": (
            "Matching selected rows does not establish complete current history or "
            "prove every annual affected-line reclassification absent. Earnings "
            "releases and interim comparisons are not independent audit opinions."
        ),
    }

for filename in ("final_05x11q1epr30.htm", "augustepr-circle_q22026f.htm"):
    REVIEWS[filename]["quotes"].append(
        "Beginning in the first quarter of 2026, we have amended the above "
        "definition of Adjusted EBITDA to exclude payroll tax expense related "
        "to stock-based compensation"
    )
    REVIEWS[filename]["finding"] += (
        " The release explicitly changes the Adjusted EBITDA definition "
        "starting in 2026; that non-GAAP definition change is not a GAAP "
        "operating-income restatement. Adjusted measures cannot substitute for "
        "reported operands."
    )
