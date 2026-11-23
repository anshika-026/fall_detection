# Draft emails: permissions and clarifications (DRAFTS ONLY, nothing has been sent)

Status: three drafts for a person to review, edit and send. No email was sent, no web form was submitted, no account was created, and nothing was downloaded.

**Before sending**
- Replace every `[PLACEHOLDER]`. The drafts deliberately contain no personal or company details.
- I could **not verify any recipient email address**. Take addresses only from the official pages named under each draft, and check that the person is still the right contact.
- Do not attach footage, credentials or internal documents. Keep a copy of each sent message and every reply; do not act on a licence statement until it is in writing.
- Have whoever is responsible for legal or licensing matters read draft A before it goes out.

---

## Draft A: ChildPose authors

**Where to find the contact:** the project page https://pediamed.ai/ChildPose/, the GitHub repository https://github.com/PediaMedAI/ChildPose (the `jiaka1chen/ChildPose` link returns 404), and the Hugging Face page https://huggingface.co/PediaMedAI/ChildPose. Use the corresponding-author address given there (not verified).

**Subject:** ChildPose: request for written permission for an internal research comparison, and enquiry about commercial licensing

Dear [AUTHOR NAME(S)],

I am writing from [COMPANY], where we develop a camera-based fall-detection system. It currently uses a general-purpose pose estimator (YOLOv8n-Pose) with person tracking and a rule-based temporal engine that works on 17 COCO keypoints. We would like to understand whether child-specific pose estimation could make the keypoints our system receives more complete or more stable for children, and we were very interested to read about ChildPose.

We have read the licence (CC BY-NC 4.0) and the Responsible Use Policy, and **we have not downloaded the weights, installed the code, or used it in any product.** We will not do so without your written agreement. We would be grateful if you could clarify the following.

1. **Internal research comparison.** We would like to run an offline, internal research comparison of ChildPose against our current estimator: same person boxes and frames, measuring keypoint visibility, confidence, missing joints, temporal stability and processing time, with no redistribution of your weights or code and nothing shipped to customers. The results would inform an internal decision about our product. Do you consider this permitted under the non-commercial research terms, given that it is carried out by a company? If not, what agreement would you need?
2. **Downloading the weights.** May we download the gated weights for that purpose, and does the gate or the Hugging Face terms add conditions beyond the licence text?
3. **Commercial evaluation and internal testing.** Is any evaluation by a commercial organisation, including internal testing, outside the licence, even when no product uses the model?
4. **Commercial licensing.** Is a commercial licence for the code and weights available, or planned? If so, what is the process, and are there any foreseeable obstacles?
5. **Upstream terms.** The model card notes that checkpoints follow the strictest upstream terms (for example Sapiens, and training sources such as ChildPlay, Children Gait Video, InfAct and the Kinetics subset). Would you be able to grant commercial rights for the checkpoints in light of these, or would a commercially clean variant need to be trained separately?
6. **Intended use.** The Responsible Use Policy prohibits covert surveillance. Our intended use is overt, safety-oriented fall detection in monitored indoor spaces, with signage and consent handled by the site operator. Is that kind of use within your policy?
7. **Scope and maturity.** Could you tell us the age range the released checkpoints are intended for (the model card says "children"; we noticed very few teenagers in the age-labelled data), whether adult performance has been measured, and whether a paper or archive link is planned?

We are happy to share our evaluation protocol and to credit your work. Thank you for your time and for releasing this work.

Kind regards,
[YOUR NAME]
[ROLE], [COMPANY]
[CONTACT DETAILS]

---

## Draft B: Principal investigator of the childcare fall study

**Where to find the contact:** the National Institute of Justice (NIJ) publication page https://www.ojp.gov/library/publications/biomechanical-characterization-video-recorded-short-distance-falls-children and the corresponding-author address of the 2022 Scientific Reports paper https://pmc.ncbi.nlm.nih.gov/articles/PMC9124183/. The project is recorded as led by Prof. Gina Bertocci, University of Louisville (NIJ award 301138): **verify the current name and address before sending.**

**Subject:** Question about future access to the childcare fall video study (3,255 recorded falls, children 12 to under 36 months)

Dear Professor [BERTOCCI / NAME],

I am writing from [COMPANY], where we work on camera-based fall detection for indoor spaces. We have read your published work on video-recorded short-distance falls of children in a licensed childcare centre, and the NIJ summary describing 3,255 recorded falls of children aged 12 to under 36 months, recorded with fixed cameras in several rooms.

We understand the dataset may not be publicly available while analysis and publication are ongoing, and **we are not assuming that any of it can be shared.** We would be grateful for guidance on the following.

1. **Status and timing.** Is the Pediatric Fall Biomechanics knowledgebase, or any part of the dataset, expected to become available after your manuscripts are published, and roughly when?
2. **What could be shared.** If sharing becomes possible, would it include anonymised video, still images, annotations (for example the fall, child and head-biomechanics descriptors), or only derived measurements? What de-identification is applied (for example faces)?
3. **Who may access it.** Is access limited to academic researchers, or could a commercial organisation request access, perhaps under a data-use agreement? Are commercial research uses permitted, and are there restrictions on product development?
4. **Consent.** Did the guardians' consent and the IRB approval cover sharing with external researchers and secondary use, including by commercial organisations? Would any new consent or an IRB amendment be required?
5. **Safeguarding and conditions.** What safeguarding, security and storage requirements would apply (for example secure storage, no attempts to identify children, no onward sharing, destruction at the end of a project)?
6. **Collaboration.** If direct data access is not possible, would you be open to a collaboration, for example evaluating a fall-detection algorithm on the data at your site under your supervision, so that no footage leaves your institution?

We have not contacted any participants or families and will not. We would respect whatever conditions you set, and we would be glad to describe our work and share our evaluation methods.

Thank you for your time.

Kind regards,
[YOUR NAME]
[ROLE], [COMPANY]
[CONTACT DETAILS]

---

## Draft C: GMDCSA-24 authors

**Where to find the contact:** the paper (E. Alam, A. Sufian, P. Dutta, M. Leo, I. A. Hameed, "GMDCSA-24: A dataset for human fall detection in videos", Data in Brief 2024;57:110892, doi 10.1016/j.dib.2024.110892; use the corresponding-author address printed in the article), the GitHub repository https://github.com/ekramalam/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos and the Zenodo record https://zenodo.org/records/12921216. Do not guess an address.

**Subject:** GMDCSA-24: subject-to-folder mapping and a question about participant-level splits

Dear Dr [ALAM / NAME],

We are using GMDCSA-24 (Zenodo v2.0, record 12921216, which we downloaded from your repository and checked against the repository's checksums) to evaluate a rule-based fall-detection system on adult footage. Thank you for releasing it under CC BY 4.0; we will cite the paper.

We want to avoid any leakage between our tuning and held-out test sets, and we noticed something we would like to check. The abstract describes **four subjects**, and the data has four folders (Subject 1 to Subject 4), but the Ethics Statement refers to **three human actors**. The room table suggests Subject 1 in Room 1, Subjects 2 and 3 in Room 2, and Subject 4 in Room 3. We have **not** tried to identify anyone from the footage and would not do so.

1. **Number of people.** How many distinct people appear in the dataset?
2. **Mapping.** Could you provide a verified participant-to-folder mapping? Anonymous labels (for example Actor A, B, C) are all we need.
3. **Repeated actors.** Does any actor appear in more than one subject folder? If so, which folders, and were different clothing, rooms or dates used?
4. **Our split.** We currently use Subjects 1 and 2 for tuning and Subjects 3 and 4 for held-out testing. Given the answers above, is that a valid participant-level split? If not, what split would you recommend?
5. **Sessions.** Were the clips in a folder recorded in one session or several (dates or days), so that sessions can also be kept apart?
6. **Participants.** Were all actors adults? (The paper does not state their ages.)
7. **Counts.** The abstract states 81 fall and 79 ADL clips, whereas the per-subject table and the CSV files give 79 fall and 81 ADL clips. Which is correct?
8. **Version.** The paper cites Zenodo version 2.1 (10.5281/zenodo.13354453) while we used v2.0 (10.5281/zenodo.12921216). Which version do you recommend for benchmarking, and what changed?
9. **Licence.** Please confirm that CC BY 4.0 (Zenodo) applies to the videos and the CSV annotations, and that the MIT licence on GitHub refers only to the repository text.
10. **Labels.** One fall clip, `Subject 4/Fall/15.mp4`, has no time range in its label. Could you tell us when the fall occurs in that clip, or confirm it should be excluded?

We would be glad to share our evaluation protocol and results. Thank you very much.

Kind regards,
[YOUR NAME]
[ROLE], [COMPANY]
[CONTACT DETAILS]
