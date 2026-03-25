# Privacy Policy

**Effective date:** March 25, 2026  
**Last updated:** March 2026

This Privacy Policy describes how **Cloud Waste Tracker** (“**we**,” “**us**,” or “**our**”) collects, uses, and shares information when you use **Cloud Waste Tracker** (the “**Service**”)—including when you connect **Amazon Web Services (“AWS”)** or use **sample/synthetic data** without a live cloud connection.

If you do not agree with this Policy, do not use the Service.

---

## 1. Who this Policy applies to

This Policy applies to visitors and users of the Service **at** **https://example.com** (and any deployed instance of the application we operate). If **you** deploy the software yourself, you should publish your own privacy notice describing **your** processing.

---

## 2. Information we collect

### 2.1 Information you provide

- **Contact or account details** if you sign up, email us, or subscribe to updates (for example name, email address).  
- **Support messages** and other communications you send.

### 2.2 Information collected automatically

- **Usage and technical data** such as **IP address**, **browser type**, **device identifiers**, **pages viewed**, **approximate timestamps**, and **diagnostic logs**—typically collected by our hosting provider and application logs.

### 2.3 Information derived from AWS (when you connect AWS)

When you run scans, the Service may process **metadata and metrics** obtained through **AWS APIs** (for example resource identifiers, regions, types, utilization signals, and **billing-related summaries** where your IAM permissions allow). This processing is **to compute waste estimates and recommendations** in the Service.

**We do not design the Service to store your long-term AWS secret access keys** in our database as a normal part of operation. Depending on configuration, **role identifiers** or **session credentials** may exist in **server memory** for the duration of a session or in **host environment variables** you configure. See **Section 5** and our technical overview at [../PRIVACY_AND_SECURITY.md](../PRIVACY_AND_SECURITY.md).

### 2.4 Information stored in our database

When scans are saved, we may store **scan records** and **findings** (for example resource identifiers, issue categories, **estimated savings in USD**, and **supplementary attributes** as JSON) to show history and recommendations.

### 2.5 Synthetic or demo data

If you use **synthetic/demo data**, that dataset does **not** come from your AWS account.

---

## 3. How we use information

We use information to:

- **Provide, operate, and improve** the Service;  
- **Authenticate** and **secure** the Service;  
- **Communicate** with you (for example service updates, security notices, support);  
- **Comply with law** and enforce our agreements;  
- **Analyze** aggregated or de-identified usage in support of reliability and product improvement.

We **do not** sell your personal information **as that term is commonly defined in “sale” privacy laws** (we do not sell your cloud inventory or scan results to data brokers for their independent use).

**We do not** use your AWS data to train **general-purpose public** machine-learning models as a core feature of the Service; if that ever changes, we will update this Policy and provide appropriate notice where required.

---

## 4. Legal bases (EEA / UK / similar jurisdictions)

Where GDPR or similar laws apply, we rely on one or more of:

- **Performance of a contract** with you;  
- **Legitimate interests** (for example securing the Service, improving reliability, fraud prevention)—balanced against your rights;  
- **Consent**, where you have given it (for example marketing cookies);  
- **Legal obligation** where required.

---

## 5. How AWS credentials and sessions work (summary)

- **Environment configuration:** Secrets used by the hosted deployment (for example database URLs, or keys for background jobs) are stored in **your hosting provider’s** secret configuration (for example Render environment variables).  
- **Browser session:** Values you enter in the app (for example **role ARN**, **external ID**, or **temporary keys**) may be held in **server-side session memory** for **that session** and are **not** intended to be stored as persistent secrets in our database **by design** of the application.  
- **You** control IAM policies, rotation, and who can access the Service URL.

This summary is **not** a substitute for your own security review.

---

## 6. How we share information

We may share information with:

- **Service providers** (subprocessors) who help us host, operate, secure, or analyze the Service (for example **cloud hosting**, **managed databases**, **logging**). They are permitted to use information only to provide services to us.  
- **Professional advisers** (lawyers, auditors) where bound by confidentiality.  
- **Authorities** when required by law, subpoena, or to protect rights, safety, or security.

---

## 7. International transfers

If you access the Service from outside the country where our servers or subprocessors are located, your information may be **transferred** across borders. Where required, we use appropriate safeguards (for example **standard contractual clauses**) or other lawful mechanisms.

---

## 8. Retention

We retain information **as long as needed** to provide the Service, comply with law, resolve disputes, and enforce agreements. **Scan and findings** data may be retained according to your deployment or **administrator settings**; **logs** may roll off after a shorter period. You may request deletion as described below, subject to legal exceptions.

---

## 9. Security

We implement **reasonable technical and organizational measures** to protect information. **No method of transmission or storage is 100% secure.** You are responsible for configuring AWS IAM, protecting your accounts, and restricting access to the Service.

---

## 10. Your rights

Depending on your location, you may have rights to **access**, **correct**, **delete**, **export**, **object to**, or **restrict** certain processing, or **withdraw consent**. To exercise rights, contact **contact@cloudwastetracker.example**. You may also lodge a complaint with your local supervisory authority.

---

## 11. California residents (summary)

If the California Consumer Privacy Act (CCPA/CPRA) applies, you may have additional rights regarding **personal information** and **sensitive** information. We do not “sell” or “share” personal information for **cross-context behavioral advertising** as part of the Service’s core design. Contact **contact@cloudwastetracker.example** for requests.

---

## 12. Children

The Service is **not directed to children under 16**. We do not knowingly collect personal information from children. If you believe we have, contact us and we will delete it.

---

## 13. Changes to this Policy

We may update this Policy from time to time. We will post the new version and update the “Last updated” date. If changes are **material**, we will provide additional notice where required by law.

---

## 14. Contact

**Cloud Waste Tracker**  
Email: **contact@cloudwastetracker.example**  
Website: **https://example.com**
