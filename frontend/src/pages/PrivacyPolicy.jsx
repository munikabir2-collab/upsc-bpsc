
function PrivacyPolicy() {
    return (
        <main style={{
            maxWidth: "900px",
            margin: "40px auto",
            padding: "24px",
            fontFamily: "Arial, sans-serif",
            lineHeight: 1.7,
            color: "#222"
        }}>
            <h1>Privacy Policy</h1>
            <p><strong>Last Updated:</strong> August 28, 2026</p>

            <h2>1. Introduction</h2>
            <p>
                UPSC-BPSC is an educational platform designed to help
                students prepare for UPSC and BPSC examinations through
                current affairs, MCQs, answer writing, and AI-powered
                learning features.
            </p>
            <p>
                We respect user privacy and are committed to protecting
                personal information.
            </p>

            <h2>2. Information We Collect</h2>
            <p>Depending on the features used, the platform may collect:</p>
            <ul>
                <li>Name</li>
                <li>Email address</li>
                <li>Account authentication information</li>
                <li>Exam preferences such as UPSC or BPSC</li>
                <li>Learning activity and submitted answers</li>
                <li>Questions and answers generated or submitted through the platform</li>
                <li>Payment-related transaction information where applicable</li>
            </ul>

            <h2>3. How We Use Information</h2>
            <p>Information may be used to:</p>
            <ul>
                <li>Create and manage user accounts</li>
                <li>Provide educational services</li>
                <li>Personalize learning features</li>
                <li>Generate and evaluate answer-writing content</li>
                <li>Process subscriptions and payments</li>
                <li>Improve platform performance and reliability</li>
                <li>Prevent unauthorized access and misuse</li>
                <li>Provide customer support</li>
            </ul>

            <h2>4. AI Services</h2>
            <p>
                Some educational features may use third-party AI services
                to generate questions, model answers, explanations, or
                evaluations.
            </p>
            <p>
                Only information necessary to provide the requested AI
                feature should be sent to such services.
            </p>

            <h2>5. Payment Information</h2>
            <p>
                Payments may be processed through third-party payment
                providers.
            </p>
            <p>
                The application does not intentionally store sensitive
                payment credentials such as card numbers, CVV, UPI PINs,
                or banking passwords.
            </p>

            <h2>6. API Keys and Secrets</h2>
            <p>
                API keys, database credentials, JWT secrets, payment
                secrets, and other confidential configuration values
                must be stored as environment variables.
            </p>
            <p>
                Users and contributors should <strong>never commit .env
                files or private API keys to the Git repository.</strong>
            </p>

            <h2>7. Data Security</h2>
            <p>Reasonable technical measures are used to protect user information, including:</p>
            <ul>
                <li>Password hashing</li>
                <li>Authentication and authorization</li>
                <li>Environment-based secret management</li>
                <li>Restricted access to confidential configuration</li>
                <li>Secure communication where HTTPS is available</li>
            </ul>
            <p>
                However, no internet-based service can guarantee
                absolute security.
            </p>

            <h2>8. Data Retention</h2>
            <p>
                User information may be retained for as long as necessary
                to provide the service, maintain account functionality,
                comply with applicable requirements, or resolve disputes.
            </p>

            <h2>9. Third-Party Services</h2>
            <p>The platform may use third-party services for functions such as:</p>
            <ul>
                <li>AI processing</li>
                <li>Payment processing</li>
                <li>Database hosting</li>
                <li>Application hosting</li>
                <li>News or content APIs</li>
            </ul>
            <p>
                These services may have their own privacy policies and terms.
            </p>

            <h2>10. Children's Privacy</h2>
            <p>
                The platform is intended primarily for educational
                examination preparation. We do not knowingly request
                unnecessary personal information from children.
            </p>

            <h2>11. Changes to This Policy</h2>
            <p>
                This Privacy Policy may be updated when platform
                functionality, technology, or legal requirements change.
            </p>
            <p>
                The updated version will be published in the repository.
            </p>

            <h2>12. Contact</h2>
            <p>
                For privacy-related questions or requests, please contact us at{" "}
                <strong>munidevika13@gmail.com</strong>.
            </p>

            <hr />

            <p><strong>UPSC-BPSC Educational Platform</strong></p>
        </main>
    );
}

export default PrivacyPolicy;
