
import React from "react";

export const OFFICIAL_SOURCES = [
  {
    key: "UPSC",
    name: "Union Public Service Commission (UPSC)",
    url: "https://upsc.gov.in/",
  },
  {
    key: "BPSC",
    name: "Bihar Public Service Commission (BPSC)",
    url: "https://bpsc.bihar.gov.in/",
  },
  {
    key: "PIB",
    name: "Press Information Bureau, Government of India",
    url: "https://pib.gov.in/",
  },
  {
    key: "INDIA",
    name: "National Portal of India",
    url: "https://www.india.gov.in/",
  },
];

const boxStyle = {
  background: "#fff8e1",
  border: "1px solid #f0c36d",
  borderRadius: 10,
  padding: "10px 12px",
  margin: "10px 0",
  fontSize: 13,
  lineHeight: 1.5,
  color: "#3d2f00",
};

const linkStyle = {
  color: "#0b57d0",
  textDecoration: "underline",
  wordBreak: "break-all",
};

function ExternalLink({ href, children }) {
  if (!href) return null;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      style={linkStyle}
    >
      {children}
    </a>
  );
}

export function DisclaimerBanner() {
  return (
    <div style={boxStyle} role="note">
      <strong>Disclaimer:</strong> This is an independent educational app.
      It is not affiliated with, endorsed by, or officially connected to UPSC,
      BPSC or any government organisation. It does not represent a government
      entity. Government information should be verified using the original
      official source.

      <br />

      <strong>सूचना:</strong> यह एक स्वतंत्र शैक्षणिक ऐप है। यह UPSC, BPSC या
      किसी सरकारी संस्था से संबद्ध अथवा अधिकृत नहीं है और किसी सरकारी निकाय
      का प्रतिनिधित्व नहीं करता। सरकारी जानकारी की पुष्टि मूल आधिकारिक स्रोत
      से करें।

      <div style={{ marginTop: 6 }}>
        <OfficialSourcesList compact />
      </div>
    </div>
  );
}

export function OfficialSourcesList({ compact = false }) {
  return (
    <div>
      {!compact && (
        <h3 style={{ fontSize: 16, margin: "8px 0" }}>
          Official Government Sources
        </h3>
      )}

      <ul style={{ margin: 0, paddingLeft: 18 }}>
        {OFFICIAL_SOURCES.map((source) => (
          <li key={source.key} style={{ margin: "2px 0" }}>
            {source.name}:{" "}
            <ExternalLink href={source.url}>
              {source.url.replace("https://", "")}
            </ExternalLink>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ArticleSourceLinks({ article }) {
  if (!article) return null;

  const publisherUrl = article.url || article.source_url || "";
  const officialUrl = article.official_source_url || "";

  return (
    <div style={{ fontSize: 12, marginTop: 8, lineHeight: 1.6 }}>
      {publisherUrl && (
        <div>
          News source:{" "}
          <ExternalLink href={publisherUrl}>
            {article.source || "Original news article"}
          </ExternalLink>
        </div>
      )}

      {officialUrl ? (
        <div>
          <strong>Verified official source:</strong>{" "}
          <ExternalLink href={officialUrl}>
            {officialUrl}
          </ExternalLink>
        </div>
      ) : (
        <div style={{ color: "#8a4b08" }}>
          Official source link has not been verified for this article.
        </div>
      )}
    </div>
  );
}
