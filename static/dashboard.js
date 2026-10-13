document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    // =====================================================
    // 1. ELEMENTS
    // =====================================================

    const $ = (id) => document.getElementById(id);

    const generateBtn = $("generateCreativeBtn");
    const regenerateBtn = $("regenerateBtn");
    const approveBtn = $("approveBtn");
    const rejectBtn = $("rejectBtn");
    const scheduleBtn = $("scheduleBtn");
    const publishBtn = $("publishBtn");

    const promptInput = $("creativePrompt");
    const formatInput = $("imageFormat");

    const imageElement = $("generatedCreativeImage");
    const placeholder = $("creativePlaceholder");

    const captionInput = $("generatedCaption");
    const hashtagsInput = $("generatedHashtags");

    const creativeMessage = $("creativeMessage");
    const contentMessage = $("contentMessage");
    const postMessage = $("postMessage");
    const scheduleMessage = $("scheduleMessage");
    const publishMessage = $("publishMessage");

    const postStatus = $("postStatus");

    const validationResult = $("validationResult");
    const validationIcon = $("validationIcon");
    const validationHeading = $("validationHeading");
    const validationProblems = $("validationProblems");

    const scheduleDateTime = $("scheduleDateTime");
    const scheduledTime = $("scheduledTime");
    const scheduleStatus = $("scheduleStatus");
    const selectedFormat = $("selectedFormat");


    // =====================================================
    // 2. DASHBOARD STATE
    // =====================================================

    let currentImage = imageElement
        ? imageElement.getAttribute("src")
        : "";

    let hasGeneratedImage = Boolean(currentImage);

    let isGenerating = false;
    let isRegenerating = false;
    let isApproving = false;
    let isRejecting = false;
    let isScheduling = false;
    let isPublishing = false;

    let currentStatus = postStatus
        ? postStatus.textContent.trim()
        : "READY";


    // =====================================================
    // 3. GENERAL HELPERS
    // =====================================================

    function showMessage(element, message, type = "") {
        if (!element) return;

        element.textContent = message;
        element.className = "message";

        if (type) {
            element.classList.add(type);
        }
    }


    function setButtonLoading(
        button,
        loading,
        loadingText,
        originalText
    ) {
        if (!button) return;

        button.disabled = loading;

        if (loading) {
            button.dataset.originalText =
                button.textContent.trim();

            button.textContent = loadingText;
        } else {
            button.textContent =
                button.dataset.originalText || originalText;
        }
    }


    function setStatus(status) {
        currentStatus = status || "READY";

        if (postStatus) {
            postStatus.textContent = currentStatus;
        }
    }


    function clearMessages() {
        [
            creativeMessage,
            contentMessage,
            postMessage,
            scheduleMessage,
            publishMessage
        ].forEach((element) => {
            showMessage(element, "");
        });
    }


    async function postJSON(url, payload = {}) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(payload)
        });

        let result;

        try {
            result = await response.json();
        } catch (error) {
            throw new Error(
                "The server returned an invalid response."
            );
        }

        if (!response.ok || result.status === "ERROR") {
            throw new Error(
                result.message || "The request failed."
            );
        }

        return result;
    }


    // Get the latest caption and hashtags from the dashboard.
    // These are sent to Flask before approval, scheduling,
    // and publishing.

    function getPostContent() {
        const caption = captionInput
            ? captionInput.value.trim()
            : "";

        const hashtagsText = hashtagsInput
            ? hashtagsInput.value.trim()
            : "";

        const hashtags = hashtagsText
            .split(/[\s,]+/)
            .map(tag => tag.trim())
            .filter(Boolean)
            .map(tag => {
                return tag.startsWith("#") ? tag : "#" + tag;
            });

        return {
            caption: caption,
            hashtags: [...new Set(hashtags)]
        };
    }


    function displayValidation(validation) {
        if (!validation || !validationResult) return;

        const passed = validation.status === "PASS";

        validationResult.className =
            "validation-box " +
            (passed
                ? "validation-success"
                : "validation-error");

        if (validationIcon) {
            validationIcon.textContent = passed ? "✓" : "!";
        }

        if (validationHeading) {
            validationHeading.textContent = passed
                ? "Validation passed"
                : "Validation requires attention";
        }

        if (validationProblems) {
            validationProblems.replaceChildren();

            const problems = validation.problems || [];

            if (problems.length === 0 && passed) {
                const paragraph = document.createElement("p");

                paragraph.textContent =
                    "Content meets the current validation rules.";

                validationProblems.appendChild(paragraph);
            } else {
                problems.forEach((problem) => {
                    const paragraph = document.createElement("p");

                    paragraph.textContent = problem;

                    validationProblems.appendChild(paragraph);
                });
            }
        }
    }


    function displayImage(imageUrl) {
        if (!imageElement || !imageUrl) return;

        const separator = imageUrl.includes("?") ? "&" : "?";

        imageElement.src =
            imageUrl + separator + "t=" + Date.now();

        imageElement.style.display = "block";

        if (placeholder) {
            placeholder.style.display = "none";
        }

        currentImage = imageUrl;
        hasGeneratedImage = true;
    }


    function clearImage() {
        if (imageElement) {
            imageElement.removeAttribute("src");
            imageElement.style.display = "none";
        }

        if (placeholder) {
            placeholder.style.display = "flex";
        }

        currentImage = "";
        hasGeneratedImage = false;
    }


    function clearGeneratedContent() {
        if (captionInput) {
            captionInput.value = "";
        }

        if (hashtagsInput) {
            hashtagsInput.value = "";
        }

        displayValidation({
            status: "FAIL",
            problems: [
                "Generate a creative to create and validate the caption."
            ]
        });

        setStatus("READY");
    }


    function getCaption() {
        return captionInput
            ? captionInput.value.trim()
            : "";
    }


    function validateScheduleTime() {
        if (!scheduleDateTime || !scheduleDateTime.value) {
            showMessage(
                scheduleMessage,
                "Please select a date and time.",
                "error"
            );

            return false;
        }

        const selectedDate = new Date(
            scheduleDateTime.value
        );

        if (Number.isNaN(selectedDate.getTime())) {
            showMessage(
                scheduleMessage,
                "Please select a valid date and time.",
                "error"
            );

            return false;
        }

        if (selectedDate <= new Date()) {
            showMessage(
                scheduleMessage,
                "Please select a future date and time.",
                "error"
            );

            return false;
        }

        return true;
    }


    function validatePostFields(messageElement) {
        if (!hasGeneratedImage) {
            showMessage(
                messageElement,
                "Generate an image before continuing.",
                "error"
            );

            return false;
        }

        const postContent = getPostContent();

        if (!postContent.caption) {
            showMessage(
                messageElement,
                "Please enter a caption before continuing.",
                "error"
            );

            return false;
        }

        return true;
    }


    // =====================================================
    // 4. IMAGE FORMAT
    // =====================================================

    if (formatInput) {
        formatInput.addEventListener("change", () => {
            if (selectedFormat) {
                selectedFormat.textContent =
                    "Selected format: " + formatInput.value;
            }
        });
    }


    // =====================================================
    // 5. GENERATE CREATIVE AND CAPTION
    // =====================================================

    if (generateBtn) {
        generateBtn.addEventListener("click", async () => {

            if (isGenerating) return;

            isGenerating = true;

            clearMessages();

            setButtonLoading(
                generateBtn,
                true,
                "Generating image and caption...",
                "Generate Creative"
            );

            clearGeneratedContent();

            showMessage(
                creativeMessage,
                "Generating your creative. This may take 1–2 minutes.",
                "info"
            );

            try {
                const prompt = promptInput
                    ? promptInput.value.trim()
                    : "";

                const format = formatInput
                    ? formatInput.value
                    : "4:5";

                const result = await postJSON(
                    "/generate-creative",
                    {
                        prompt: prompt,
                        image_format: format
                    }
                );

                if (result.image) {
                    displayImage(result.image);
                }

                if (captionInput) {
                    captionInput.value =
                        result.caption || "";
                }

                if (hashtagsInput) {
                    const hashtags = result.hashtags || [];

                    hashtagsInput.value =
                        Array.isArray(hashtags)
                            ? hashtags.join(" ")
                            : hashtags;
                }

                displayValidation(result.validation);

                setStatus(result.post_status || "READY");

                showMessage(
                    creativeMessage,
                    result.message ||
                        "Creative and caption generated successfully.",
                    "success"
                );

                showMessage(
                    contentMessage,
                    "Caption and hashtags generated successfully.",
                    "success"
                );

            } catch (error) {
                console.error(
                    "Creative generation error:",
                    error
                );

                showMessage(
                    creativeMessage,
                    error.message ||
                        "Unable to generate creative.",
                    "error"
                );

            } finally {
                isGenerating = false;

                setButtonLoading(
                    generateBtn,
                    false,
                    "",
                    "Generate Creative"
                );
            }
        });
    }


    // =====================================================
    // 6. REGENERATE CONTENT
    // =====================================================

    if (regenerateBtn) {
        regenerateBtn.addEventListener("click", async () => {

            if (isRegenerating) return;

            isRegenerating = true;

            clearMessages();

            setButtonLoading(
                regenerateBtn,
                true,
                "Regenerating...",
                "Regenerate content"
            );

            try {
                const result = await postJSON(
                    "/regenerate",
                    {}
                );

                clearImage();
                clearGeneratedContent();

                if (promptInput) {
                    promptInput.value = "";
                }

                if (result.validation) {
                    displayValidation(result.validation);
                }

                setStatus(result.post_status || "READY");

                showMessage(
                    contentMessage,
                    result.message ||
                        "New plan created. Generate a creative to create a new caption.",
                    "success"
                );

            } catch (error) {
                console.error(
                    "Content regeneration error:",
                    error
                );

                showMessage(
                    contentMessage,
                    error.message ||
                        "Unable to regenerate content.",
                    "error"
                );

            } finally {
                isRegenerating = false;

                setButtonLoading(
                    regenerateBtn,
                    false,
                    "",
                    "Regenerate content"
                );
            }
        });
    }


    // =====================================================
    // 7. APPROVE POST
    // =====================================================

    if (approveBtn) {
        approveBtn.addEventListener("click", async () => {

            if (isApproving) return;

            if (!validatePostFields(postMessage)) return;

            isApproving = true;

            setButtonLoading(
                approveBtn,
                true,
                "Approving...",
                "✓ Approve"
            );

            showMessage(
                postMessage,
                "Checking content and image safety...",
                "info"
            );

            try {
                const result = await postJSON(
                    "/approve",
                    getPostContent()
                );

                setStatus(
                    result.post_status || "APPROVED"
                );

                if (result.validation) {
                    displayValidation(result.validation);
                }

                showMessage(
                    postMessage,
                    result.message ||
                        "Post approved successfully.",
                    "success"
                );

            } catch (error) {
                showMessage(
                    postMessage,
                    error.message || "Approval failed.",
                    "error"
                );

            } finally {
                isApproving = false;

                setButtonLoading(
                    approveBtn,
                    false,
                    "",
                    "✓ Approve"
                );
            }
        });
    }


    // =====================================================
    // 8. REJECT POST
    // =====================================================

    if (rejectBtn) {
        rejectBtn.addEventListener("click", async () => {

            if (isRejecting) return;

            isRejecting = true;

            setButtonLoading(
                rejectBtn,
                true,
                "Rejecting...",
                "Reject"
            );

            try {
                const result = await postJSON(
                    "/reject",
                    {}
                );

                setStatus(
                    result.post_status || "REJECTED"
                );

                showMessage(
                    postMessage,
                    result.message || "Post rejected.",
                    "success"
                );

            } catch (error) {
                showMessage(
                    postMessage,
                    error.message ||
                        "Unable to reject post.",
                    "error"
                );

            } finally {
                isRejecting = false;

                setButtonLoading(
                    rejectBtn,
                    false,
                    "",
                    "Reject"
                );
            }
        });
    }


    // =====================================================
    // 9. SCHEDULE POST
    // =====================================================

    if (scheduleBtn) {
        scheduleBtn.addEventListener("click", async () => {

            if (isScheduling) return;

            if (currentStatus !== "APPROVED") {
                showMessage(
                    scheduleMessage,
                    "Approve the post before scheduling.",
                    "error"
                );

                return;
            }

            if (!validatePostFields(scheduleMessage)) return;

            if (!validateScheduleTime()) return;

            isScheduling = true;

            setButtonLoading(
                scheduleBtn,
                true,
                "Scheduling...",
                "Schedule post"
            );

            try {
                const result = await postJSON(
                    "/schedule",
                    {
                        ...getPostContent(),
                        scheduled_datetime:
                            scheduleDateTime.value
                    }
                );

                setStatus(
                    result.post_status || "SCHEDULED"
                );

                if (scheduledTime) {
                    scheduledTime.textContent =
                        result.post?.scheduled_datetime ||
                        scheduleDateTime.value;
                }

                if (scheduleStatus) {
                    scheduleStatus.textContent = "SCHEDULED";
                }

                showMessage(
                    scheduleMessage,
                    result.message ||
                        "Post scheduled successfully.",
                    "success"
                );

            } catch (error) {
                showMessage(
                    scheduleMessage,
                    error.message ||
                        "Unable to schedule post.",
                    "error"
                );

            } finally {
                isScheduling = false;

                setButtonLoading(
                    scheduleBtn,
                    false,
                    "",
                    "Schedule post"
                );
            }
        });
    }


    // =====================================================
    // 10. PUBLISH TO INSTAGRAM
    // =====================================================

    if (publishBtn) {
        publishBtn.addEventListener("click", async () => {

            if (isPublishing) return;

            if (!validatePostFields(publishMessage)) return;

            if (
                currentStatus !== "APPROVED" &&
                currentStatus !== "SCHEDULED"
            ) {
                showMessage(
                    publishMessage,
                    "Approve the post before publishing.",
                    "error"
                );

                return;
            }

            const confirmed = window.confirm(
                "Are you sure you want to publish this post to Instagram?"
            );

            if (!confirmed) return;

            isPublishing = true;

            setButtonLoading(
                publishBtn,
                true,
                "Publishing...",
                "Publish to Instagram"
            );

            showMessage(
                publishMessage,
                "Publishing your post...",
                "info"
            );

            try {
                const result = await postJSON(
                    "/publish",
                    getPostContent()
                );

                setStatus(
                    result.post_status || "PUBLISHED"
                );

                showMessage(
                    publishMessage,
                    result.message ||
                        "Post published successfully.",
                    "success"
                );

            } catch (error) {
                console.error(
                    "Instagram publishing error:",
                    error
                );

                showMessage(
                    publishMessage,
                    error.message ||
                        "Unable to publish to Instagram.",
                    "error"
                );

            } finally {
                isPublishing = false;

                setButtonLoading(
                    publishBtn,
                    false,
                    "",
                    "Publish to Instagram"
                );
            }
        });
    }


    // =====================================================
    // 11. INITIAL PAGE STATE
    // =====================================================

    if (imageElement && imageElement.getAttribute("src")) {
        imageElement.addEventListener("error", () => {
            imageElement.style.display = "none";

            if (placeholder) {
                placeholder.style.display = "flex";
            }

            hasGeneratedImage = false;
        });
    }

    console.log("SocialPilot AI dashboard initialized.");

});