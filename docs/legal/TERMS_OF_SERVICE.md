# Terms of Use

**Effective date:** March 25, 2026  
**Last updated:** March 2026

These Terms of Use (“**Terms**”) govern your access to and use of the Cloud Waste Tracker **Service** (the website, application, APIs, and related functionality) offered by **Cloud Waste Tracker** (“**we**,” “**us**,” or “**our**”). By accessing or using the Service, you agree to these Terms. If you do not agree, do not use the Service.

---

## 1. Who may use the Service

You must be **at least 18 years old** (or the age of majority in your jurisdiction) and have authority to bind yourself and, if applicable, the organization you represent. If you use the Service on behalf of a company or other entity, you represent that you have authority to accept these Terms on its behalf.

---

## 2. What the Service does

The Service provides **cloud cost and waste insights**, including **estimated** dollar figures and **recommendations** based on data obtained from your cloud provider (for example **Amazon Web Services (“AWS”)**) when you choose to connect an account or run a scan. The Service may also offer **sample or synthetic data** modes that do not require a live cloud connection.

The Service is **not** a substitute for your own judgment, internal FinOps or engineering review, or professional advice.

---

## 3. AWS connection, credentials, and your responsibilities

### 3.1 Your cloud account

You retain sole responsibility for **your AWS account**, **IAM policies**, **security**, **compliance**, and **billing** with AWS and any other providers you use.

### 3.2 How access is intended to work

When you connect AWS, the Service is designed to use **AWS APIs in a read-oriented way** (for example, to **describe**, **list**, or **get** resources and, where you grant permission, **Cost Explorer** or similar read APIs) to compute estimates and recommendations. **The Service does not exist to modify your infrastructure**; any changes to your resources should be made **by you** in AWS (or through tools you control).

### 3.3 Credentials and configuration

Depending on deployment and configuration, authentication may involve **AssumeRole**, **access keys**, **session tokens**, or **environment-based credentials** on the host running the Service. You are responsible for:

- Granting **least-privilege** IAM permissions appropriate to your risk tolerance;  
- **Rotating** and **protecting** secrets;  
- Ensuring that **only authorized people** can access URLs, API keys, or environments where credentials exist.

We describe how the software **is built to handle** credentials in our technical overview and Privacy Policy; **your deployment and AWS configuration** may differ.

### 3.4 No endorsement

References to AWS or other third-party services are for description only. AWS is a trademark of Amazon.com, Inc. or its affiliates. We are **not** sponsored or endorsed by AWS.

---

## 4. Acceptable use

You agree **not** to:

- Use the Service in violation of law or third-party rights;  
- Attempt to probe, scan, or test the vulnerability of the Service or other accounts without authorization;  
- Interfere with or disrupt the Service or other users;  
- Reverse engineer the Service except where prohibited by law;  
- Use the Service to transmit malware or unlawful content;  
- Misrepresent savings, billing, or compliance to third parties based on the Service’s output.

We may suspend or terminate access if we reasonably believe you have violated these Terms or create risk or legal exposure for us or others.

---

## 5. Accounts and access

If the Service uses passwords, invitations, or single sign-on, you are responsible for safeguarding login credentials. **If you deploy the Service yourself**, you are responsible for network access, authentication in front of the app, and secrets management.

---

## 6. Intellectual property

We (or our licensors) own the Service, including software, branding, and documentation. Subject to these Terms, we grant you a **limited, non-exclusive, non-transferable, revocable** license to use the Service for your internal business purposes. You may not copy, modify, distribute, sell, or lease the Service except as allowed by law or with our written permission.

Feedback you give us may be used without obligation to you.

---

## 7. Third-party services and links

The Service may link to third-party sites or rely on third-party infrastructure (for example hosting or databases). Those services are governed by their own terms. We are not responsible for third-party services.

---

## 8. Disclaimers — read carefully

**TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW:**

### 8.1 “AS IS”

THE SERVICE IS PROVIDED **“AS IS”** AND **“AS AVAILABLE,”** WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, OR STATUTORY, INCLUDING IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT.

### 8.2 Estimates and recommendations

**DOLLAR AMOUNTS, “WASTE” FIGURES, SAVINGS ESTIMATES, AND RECOMMENDATIONS ARE INFORMATIONAL AND APPROXIMATE.** They depend on AWS APIs, heuristics, pricing assumptions, timing delays, tagging, and incomplete data. **THEY ARE NOT GUARANTEES** of actual invoices, refunds, credits, or business outcomes. **YOU ARE SOLELY RESPONSIBLE** for verifying costs and changes in your cloud consoles and bills before taking action.

### 8.3 No professional advice

NOTHING IN THE SERVICE IS **FINANCIAL, TAX, LEGAL, OR COMPLIANCE ADVICE.** Consult qualified professionals for decisions that could affect your business, taxes, or regulatory obligations.

### 8.4 No guarantee of availability

We do not warrant that the Service will be uninterrupted, error-free, or free of harmful components.

Some jurisdictions do not allow certain disclaimers; in those jurisdictions, our warranties are limited to the fullest extent permitted.

---

## 9. Limitation of liability

**TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW:**

### 9.1 Exclusion of damages

IN NO EVENT WILL **Cloud Waste Tracker** OR ITS SUPPLIERS BE LIABLE FOR ANY **INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES**, OR ANY LOSS OF **PROFITS, REVENUE, DATA, GOODWILL**, OR **BUSINESS INTERRUPTION**, ARISING OUT OF OR RELATED TO THE SERVICE OR THESE TERMS, EVEN IF ADVISED OF THE POSSIBILITY.

### 9.2 Liability cap

OUR **TOTAL** LIABILITY FOR ANY CLAIM ARISING OUT OF OR RELATING TO THE SERVICE OR THESE TERMS WILL NOT EXCEED THE **GREATER OF** (A) THE AMOUNTS YOU PAID US FOR THE SERVICE IN THE **TWELVE (12) MONTHS** BEFORE THE CLAIM, OR **(B) ONE HUNDRED U.S. DOLLARS (USD $100)** IF YOU HAVE NOT PAID FEES.

### 9.3 Basis of the bargain

THE LIMITATIONS IN THIS SECTION ARE AN ESSENTIAL BASIS OF THE BARGAIN BETWEEN YOU AND US.

Some jurisdictions do not allow certain limitations; in those jurisdictions, our liability is limited to the fullest extent permitted.

---

## 10. Indemnity

You will **defend, indemnify, and hold harmless** **Cloud Waste Tracker** and its officers, directors, employees, and agents from and against any claims, damages, losses, and expenses (including reasonable attorneys’ fees) arising out of or related to **your use of the Service**, **your AWS accounts and IAM configuration**, **your violation of these Terms**, or **your violation of third-party rights**.

---

## 11. Privacy

Our **[Privacy Policy](PRIVACY_POLICY.md)** explains how we collect, use, and share information. By using the Service, you acknowledge that policy.

*(When publishing, replace the relative link with the public URL of your Privacy Policy.)*

---

## 12. Term and termination

We may change, suspend, or discontinue the Service (in whole or part) at any time. You may stop using the Service at any time. Provisions that by their nature should survive (including **Disclaimers**, **Limitation of Liability**, **Indemnity**, and **Governing Law**) will survive termination.

---

## 13. Changes to these Terms

We may modify these Terms by posting an updated version and updating the “Last updated” date. If changes are **material**, we will take reasonable steps to notify you (for example by email or in-app notice) where practicable. **Continued use after the effective date** of changes constitutes acceptance. If you do not agree, stop using the Service.

---

## 14. Governing law and disputes

These Terms are governed by applicable law. **Exclusive venue** for disputes will be determined by the applicable courts unless prohibited by law. **Informal resolution first:** before filing a claim, you agree to contact us at **contact@cloudwastetracker.example** to try to resolve the dispute.

---

## 15. Export and sanctions

You represent that you are not located in a country subject to embargoes or sanctions that would prohibit use of the Service, and that you are not on a denied-party list.

---

## 16. Miscellaneous

**Entire agreement.** These Terms and the Privacy Policy are the entire agreement about the Service.  
**Assignment.** You may not assign these Terms without our consent; we may assign them in connection with a merger or sale.  
**No waiver.** Failure to enforce a provision is not a waiver.  
**Severability.** If a provision is invalid, the remainder stays in effect.  
**Notices.** We may notify you via the Service or the email associated with your account. Notices to us: **contact@cloudwastetracker.example**.

---

## 17. Contact

**Cloud Waste Tracker**  
Email: **contact@cloudwastetracker.example**  
Website: **https://example.com**
