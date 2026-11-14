(function () {
  "use strict";

  const MAX_AVATAR_SIZE = 5 * 1024 * 1024;
  const ALLOWED_AVATAR_TYPES = new Set([
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif"
  ]);
  const CAREER_REQUIRED_TYPES = new Set([
    "estudiante",
    "docente",
    "investigador",
    "egresado"
  ]);

  function showEditModal(scrollToAvatar) {
    const modal = document.getElementById("editProfileModal");
    if (!modal || typeof window.jQuery === "undefined") {
      return;
    }

    window.jQuery(modal).modal("show");

    if (scrollToAvatar) {
      window.setTimeout(function () {
        document.querySelector(".avatar-upload-container")?.scrollIntoView({
          behavior: "smooth",
          block: "center"
        });
      }, 300);
    }
  }

  function updateAvatarPreview(dataUrl) {
    const preview = document.getElementById("avatarPreview");
    if (!preview) {
      return;
    }

    if (preview instanceof HTMLImageElement) {
      preview.src = dataUrl;
      return;
    }

    const image = document.createElement("img");
    image.src = dataUrl;
    image.alt = "Vista previa del avatar";
    image.className = "avatar-preview-image";
    preview.replaceChildren(image);
    preview.classList.remove("avatar-placeholder");
  }

  function previewAvatar(input) {
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    if (file.size > MAX_AVATAR_SIZE) {
      window.alert(gettext("El archivo es demasiado grande. Máximo 5 MB permitido."));
      input.value = "";
      return;
    }

    if (!ALLOWED_AVATAR_TYPES.has(file.type)) {
      window.alert(gettext("Formato de archivo no válido. Usa JPG, PNG o GIF."));
      input.value = "";
      return;
    }

    const reader = new FileReader();
    reader.addEventListener("load", function () {
      if (typeof reader.result === "string") {
        updateAvatarPreview(reader.result);
      }
    });
    reader.readAsDataURL(file);
  }

  function scheduleAlertDismissal() {
    document.querySelectorAll(".profile-alert").forEach(function (alert) {
      window.setTimeout(function () {
        alert.classList.add("profile-alert--hidden");
        window.setTimeout(function () {
          alert.remove();
        }, 300);
      }, 5000);
    });
  }

  function initializeInstitutionalFields() {
    const form = document.getElementById("profileInstitutionalForm");
    const type = document.getElementById("profileTipoUsuario");
    const faculty = document.getElementById("profileFacultad");
    const career = document.getElementById("profileCarrera");
    const careerHelp = document.getElementById("profileCarreraHelp");

    if (!form || !type || !faculty || !career) {
      return;
    }

    const wrappers = new Map();
    form.querySelectorAll("[data-profile-edit-field]").forEach(function (field) {
      wrappers.set(field.dataset.profileEditField, field);
    });

    function setFieldVisibility(name, visible) {
      const wrapper = wrappers.get(name);
      if (!wrapper) {
        return;
      }
      wrapper.hidden = !visible;
      wrapper.querySelectorAll("input, select, textarea").forEach(function (control) {
        control.disabled = !visible;
      });
    }

    function filterCareers(resetInvalid) {
      const selectedFaculty = faculty.value;
      const selectedOption = career.selectedOptions[0];

      if (
        resetInvalid &&
        selectedOption?.value &&
        selectedOption.dataset.facultad !== selectedFaculty
      ) {
        career.value = "";
      }

      career.querySelectorAll("option[data-facultad]").forEach(function (option) {
        const matches = Boolean(selectedFaculty) && option.dataset.facultad === selectedFaculty;
        const preserveInvalidSelection = !resetInvalid && option.selected;
        option.hidden = !(matches || preserveInvalidSelection);
        option.disabled = !(matches || preserveInvalidSelection);
      });

      const isExternal = type.value === "externo";
      career.disabled = isExternal || !selectedFaculty;

      if (!careerHelp) {
        return;
      }
      if (!selectedFaculty) {
        careerHelp.textContent = gettext("Selecciona primero una facultad para ver sus carreras.");
      } else if (career.querySelectorAll("option[data-facultad]:not([disabled])").length === 0) {
        careerHelp.textContent = CAREER_REQUIRED_TYPES.has(type.value)
          ? gettext("Selecciona una facultad académica que tenga carreras asociadas.")
          : "Esta dependencia no tiene carreras asociadas; puedes continuar sin seleccionar una.";
      } else if (CAREER_REQUIRED_TYPES.has(type.value)) {
        careerHelp.textContent = gettext("Selecciona la carrera asociada a tu perfil institucional.");
      } else {
        careerHelp.textContent = "Opcional para personal administrativo; selecciónala si estás vinculado a un programa académico.";
      }
    }

    function updateInstitutionalFields(resetCareer) {
      const isExternal = type.value === "externo";
      const isStudent = type.value === "estudiante";
      const careerRequired = CAREER_REQUIRED_TYPES.has(type.value);

      setFieldVisibility("institucion", isExternal);
      setFieldVisibility("facultad", !isExternal);
      setFieldVisibility("carrera", !isExternal);
      setFieldVisibility("nivel_academico", isStudent);
      // La cédula identifica a cualquier persona, no solo al estudiante; para
      // él además es obligatoria.
      setFieldVisibility("cedula", true);

      faculty.required = !isExternal;
      career.required = !isExternal && careerRequired;
      document.getElementById("profileInstitucion")?.toggleAttribute("required", isExternal);
      document.getElementById("profileNivelAcademico")?.toggleAttribute("required", isStudent);
      document.getElementById("profileCedula")?.toggleAttribute("required", isStudent);

      form.querySelectorAll("[data-cedula-required-indicator]").forEach(function (indicator) {
        indicator.hidden = !isStudent;
      });
      form.querySelectorAll("[data-career-required-indicator]").forEach(function (indicator) {
        indicator.hidden = isExternal || !careerRequired;
      });
      filterCareers(Boolean(resetCareer));
    }

    type.addEventListener("change", function () {
      updateInstitutionalFields(false);
    });
    faculty.addEventListener("change", function () {
      filterCareers(true);
    });
    updateInstitutionalFields(false);
  }

  function reopenInvalidProfileModal() {
    const modal = document.getElementById("editProfileModal");
    if (!modal || modal.dataset.openOnLoad !== "true") {
      return;
    }
    showEditModal(false);
    window.jQuery?.(modal).one("shown.bs.modal", function () {
      modal.querySelector(".is-invalid")?.scrollIntoView({
        behavior: "smooth",
        block: "center"
      });
    });
  }

  function initializeProfile() {
    document.getElementById("openEditModalButton")?.addEventListener("click", function () {
      showEditModal(false);
    });

    document.getElementById("openAvatarModalButton")?.addEventListener("click", function () {
      showEditModal(true);
    });

    document.getElementById("avatarUploadTrigger")?.addEventListener("click", function () {
      document.getElementById("avatarInput")?.click();
    });

    document.getElementById("avatarInput")?.addEventListener("change", function (event) {
      previewAvatar(event.currentTarget);
    });

    initializeInstitutionalFields();
    reopenInvalidProfileModal();
    scheduleAlertDismissal();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeProfile, { once: true });
  } else {
    initializeProfile();
  }
})();
