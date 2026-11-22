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
  lineHeight: 1.6,
  color: "#3d2f00",
};

const linkStyle = {
  color: "#0b57d0",
  textDecoration: "underline",
  wordBreak: "break-all",
};
const detailsStyle = {
  marginTop: 8,
  padding: "8px 10px",
  background: "rgba(255,255,255,0.65)",
  border: "1px solid #ead49c",
  borderRadius: 7,
};

const summaryStyle = {
  cursor: "pointer",
  fontWeight: 600,
  color: "#594300",
};
function isSafeHttpsUrl(value) {
  if (!value || typeof value !== "string") return false;

  try {
    const parsed = new URL(value);

    return (
      parsed.protocol === "https:" &&
      Boolean(parsed.hostname) &&
      !parsed.username &&
      !parsed.password
    );
  } catch {
    return false;
  }
}


function isOfficialGovernmentUrl(value) {
  if (!isSafeHttpsUrl(value)) return false;

  try {
    const hostname = new URL(value).hostname.toLowerCase();

    return (
      hostname === "gov.in" ||
      hostname.endsWith(".gov.in") ||
      hostname === "nic.in" ||
      hostname.endsWith(".nic.in") ||
      hostname === "rbi.org.in"
    );
  } catch {
    return false;
  }
}

function ExternalLink({ href, children }) {
  if (!isSafeHttpsUrl(href)) return null;

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
      <strong>Important Disclaimer / महत्वपूर्ण सूचना:</strong>

      <div style={{ marginTop: 4 }}>
        Muni48 is an independent educational platform. It is not
        affiliated with UPSC, BPSC or any government body.
      </div>

      <div style={{ marginTop: 4 }}>
        Muni48 एक स्वतंत्र शैक्षणिक प्लेटफॉर्म है। इसका UPSC, BPSC
        या किसी सरकारी संस्था से आधिकारिक संबंध नहीं है।
      </div>

      <details style={detailsStyle}>
        <summary style={summaryStyle}>
          Read full disclaimer / पूरी सूचना पढ़ें
        </summary>

        <div style={{ marginTop: 8 }}>
          <strong>Important Disclaimer:</strong>
          <p>
            This is an independent educational application. It is not
            affiliated with, endorsed by, or officially connected to
            UPSC, BPSC, PIB, or any government department or organisation.
            It does not represent a government entity.
          </p>
          <p>
            Government-related information should always be checked
            against the original source published by the relevant
            government authority.
          </p>

          <strong>महत्वपूर्ण सूचना:</strong>
          <p>
            यह एक स्वतंत्र शैक्षणिक ऐप है। इसका UPSC, BPSC, PIB या
            किसी सरकारी विभाग अथवा संस्था से कोई आधिकारिक संबंध या
            संबद्धता नहीं है। यह किसी सरकारी निकाय का प्रतिनिधित्व
            नहीं करता।
          </p>
          <p>
            सरकारी जानकारी की पुष्टि संबंधित सरकारी प्राधिकरण द्वारा
            प्रकाशित मूल स्रोत से अवश्य करें।
          </p>
        </div>
      </details>

      <details style={detailsStyle}>
        <summary style={summaryStyle}>
          Official Government Portals / आधिकारिक सरकारी पोर्टल
        </summary>

        <div style={{ marginTop: 8 }}>
          <OfficialSourcesList compact />
        </div>
      </details>
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
          <li key={source.key} style={{ margin: "3px 0" }}>
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

  const publisherUrl =
    article.url || article.source_url || "";

  const officialUrl =
    article.official_source_url || "";

  const hasPublisherLink =
    isSafeHttpsUrl(publisherUrl);

  const hasVerifiedOfficialLink =
    isOfficialGovernmentUrl(officialUrl);

  return (
    <div
      style={{
        fontSize: 12,
        marginTop: 8,
        lineHeight: 1.7,
        overflowWrap: "anywhere",
      }}
    >
      {hasPublisherLink && (
        <div>
          <strong>News Publisher Source:</strong>{" "}
          <ExternalLink href={publisherUrl}>
            {article.source || "Read original news article"}
          </ExternalLink>
        </div>
      )}

      {hasVerifiedOfficialLink ? (
        <div style={{ marginTop: 5 }}>
          <strong>
            Verified Government Source / सत्यापित सरकारी स्रोत:
          </strong>{" "}
          <ExternalLink href={officialUrl}>
            Open original government publication
          </ExternalLink>
        </div>
      ) : (
        <div
          style={{
            marginTop: 5,
            padding: "7px 9px",
            background: "#fff8e1",
            border: "1px solid #f0c36d",
            borderRadius: 6,
            color: "#8a4b08",
          }}
        >
          <strong>Government source not verified.</strong>
          <br />
          The original government publication link has not been verified
          for this article. Do not treat this article as an officially
          verified government announcement.

          <br />

          <strong>सरकारी स्रोत सत्यापित नहीं है।</strong>
          इस लेख के लिए मूल सरकारी प्रकाशन का लिंक सत्यापित नहीं हुआ है।
          इसे आधिकारिक रूप से सत्यापित सरकारी घोषणा न मानें।
        </div>
      )}
    </div>
  );
}
