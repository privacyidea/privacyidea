/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import {
  DAYPASSWORD_HASHLIB,
  DAYPASSWORD_TIME_STEP,
  QUESTION_NUMBER_OF_ANSWERS,
  REMOTE_VERIFY_SSL,
  TIQR_INFO_URL,
  TIQR_LOGO_URL,
  TIQR_OCRASUITE,
  TIQR_REG_SERVER,
  YUBICO_ID,
  YUBICO_SECRET,
  YUBICO_URL
} from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";
import {
  isQuestionKey,
  panelCompleteness,
  systemConfigDiffers,
  toSystemConfig,
  toTokenTypeConfigModel,
  TOKEN_TYPE_CONFIG_KEYS,
  YUBICO_KEYS
} from "./token-type-config.form";

const kinds = (field: { errors(): { kind: string }[] }) => field.errors().map((error) => error.kind);

describe("token type config form", () => {
  describe("toTokenTypeConfigModel", () => {
    it("holds every panel key, empty when the backend has none", () => {
      const model = toTokenTypeConfigModel({ other: "kept" });
      for (const key of TOKEN_TYPE_CONFIG_KEYS) {
        expect(model.values[key]).toBe("");
      }
      expect(model.values["other"]).toBe("kept");
    });

    it("treats a null backend value of a panel key as empty", () => {
      const model = toTokenTypeConfigModel({ [TIQR_OCRASUITE]: null as unknown as string });
      expect(model.values[TIQR_OCRASUITE]).toBe("");
    });

    it("keeps the backend value of a panel key", () => {
      expect(toTokenTypeConfigModel({ [TIQR_OCRASUITE]: "suite" }).values[TIQR_OCRASUITE]).toBe("suite");
    });

    it("moves the SSL flag out of the values and parses it", () => {
      const checked = toTokenTypeConfigModel({ [REMOTE_VERIFY_SSL]: "True" });
      expect(checked.verifySsl).toBe(true);
      expect(checked.values).not.toHaveProperty(REMOTE_VERIFY_SSL);
      expect(toTokenTypeConfigModel({ [REMOTE_VERIFY_SSL]: "False" }).verifySsl).toBe(false);
      expect(toTokenTypeConfigModel({}).verifySsl).toBe(false);
    });
  });

  describe("toSystemConfig", () => {
    it("adds nothing for a panel key the backend does not hold and that is empty", () => {
      expect(toSystemConfig(toTokenTypeConfigModel({}), {})).toEqual({});
    });

    it("keeps an empty value the backend holds", () => {
      const backend = { [TIQR_OCRASUITE]: "" };
      expect(toSystemConfig(toTokenTypeConfigModel(backend), backend)).toEqual(backend);
    });

    it("leaves out an empty entry the backend defaults, even when the backend holds it", () => {
      const backend = { [YUBICO_URL]: "https://yubico.example", [DAYPASSWORD_HASHLIB]: "sha1" };
      const model = toTokenTypeConfigModel(backend);
      model.values[YUBICO_URL] = "";
      model.values[DAYPASSWORD_HASHLIB] = "";
      expect(toSystemConfig(model, backend)).toEqual({});
    });

    it("keeps an empty value of an entry no panel edits", () => {
      const model = toTokenTypeConfigModel({});
      model.values["yubikey.apiid.ID"] = "";
      expect(toSystemConfig(model, {})).toEqual({ "yubikey.apiid.ID": "" });
    });

    it("writes a value the user typed", () => {
      const model = toTokenTypeConfigModel({});
      model.values[TIQR_OCRASUITE] = "suite";
      expect(toSystemConfig(model, {})).toEqual({ [TIQR_OCRASUITE]: "suite" });
    });

    describe("SSL flag", () => {
      it("is left out while the backend has none and the box is unchecked", () => {
        expect(toSystemConfig({ values: {}, verifySsl: false }, {})).toEqual({});
      });

      it("is written as True once the box is checked", () => {
        expect(toSystemConfig({ values: {}, verifySsl: true }, {})).toEqual({ [REMOTE_VERIFY_SSL]: "True" });
      });

      it("is written as False when the box is unchecked and the backend has a value", () => {
        expect(toSystemConfig({ values: {}, verifySsl: false }, { [REMOTE_VERIFY_SSL]: "True" })).toEqual({
          [REMOTE_VERIFY_SSL]: "False"
        });
      });

      it("keeps the backend spelling while the meaning is unchanged", () => {
        expect(toSystemConfig({ values: {}, verifySsl: true }, { [REMOTE_VERIFY_SSL]: "true" })).toEqual({
          [REMOTE_VERIFY_SSL]: "true"
        });
      });
    });
  });

  describe("systemConfigDiffers", () => {
    it("is false for equal configs", () => {
      expect(systemConfigDiffers({ a: "1" }, { a: "1" })).toBe(false);
    });

    it("is true for a different value, a missing key and an extra key", () => {
      expect(systemConfigDiffers({ a: "2" }, { a: "1" })).toBe(true);
      expect(systemConfigDiffers({ a: "1" }, { a: "1", b: "2" })).toBe(true);
      expect(systemConfigDiffers({ a: "1", b: "2" }, { a: "1" })).toBe(true);
    });
  });

  it("recognises question keys", () => {
    expect(isQuestionKey("question.question.3")).toBe(true);
    expect(isQuestionKey(QUESTION_NUMBER_OF_ANSWERS)).toBe(false);
  });

  describe("panelCompleteness", () => {
    const setValue = (model: ReturnType<typeof createTokenTypeConfigForm>["model"], key: string, value: string) =>
      model.update((current) => ({ ...current, values: { ...current.values, [key]: value } }));

    it("is complete for an empty panel and incomplete while a started panel has an invalid entry", () => {
      const { form, model } = createTokenTypeConfigForm();
      const { incomplete } = panelCompleteness(
        () => form,
        () => YUBICO_KEYS
      );
      expect(incomplete()).toBe(false);

      setValue(model, YUBICO_ID, "12345");
      expect(incomplete()).toBe(true);

      setValue(model, YUBICO_SECRET, "key");
      expect(incomplete()).toBe(false);
    });

    it("only looks at the keys of its own panel", () => {
      const { form } = createTokenTypeConfigForm({ [TIQR_OCRASUITE]: "suite" });
      const { incomplete } = panelCompleteness(
        () => form,
        () => YUBICO_KEYS
      );
      expect(form().valid()).toBe(false);
      expect(incomplete()).toBe(false);
    });

    it("ignores a key the form does not hold", () => {
      const { form } = createTokenTypeConfigForm();
      const { incomplete } = panelCompleteness(
        () => form,
        () => ["unknown.key"]
      );
      expect(incomplete()).toBe(false);
    });

    it("reveals the panel once it is incomplete and stays revealed after it is completed", () => {
      const { form, model } = createTokenTypeConfigForm();
      const { revealed } = panelCompleteness(
        () => form,
        () => YUBICO_KEYS
      );
      expect(revealed()).toBe(false);

      setValue(model, YUBICO_ID, "12345");
      expect(revealed()).toBe(true);

      setValue(model, YUBICO_SECRET, "key");
      expect(revealed()).toBe(true);
    });
  });

  describe("rules", () => {
    it("is valid for an empty config", () => {
      expect(createTokenTypeConfigForm().form().valid()).toBe(true);
    });

    it("applies no rule to a panel while it is empty", () => {
      const { form } = createTokenTypeConfigForm();
      expect(kinds(form.values[DAYPASSWORD_TIME_STEP]())).toEqual([]);
      expect(kinds(form.values[TIQR_REG_SERVER]())).toEqual([]);
      expect(kinds(form.values[YUBICO_ID]())).toEqual([]);
    });

    it("requires no DayPassword entry, the backend defaults both", () => {
      const { form } = createTokenTypeConfigForm({ [DAYPASSWORD_HASHLIB]: "sha1" });
      expect(kinds(form.values[DAYPASSWORD_TIME_STEP]())).toEqual([]);
      expect(
        createTokenTypeConfigForm({ [DAYPASSWORD_TIME_STEP]: "1d" })
          .form()
          .valid()
      ).toBe(true);
      expect(form().valid()).toBe(true);
    });

    it("requires the registration server and logo of TiQR once one entry is filled, not the info URL", () => {
      const { form } = createTokenTypeConfigForm({ [TIQR_OCRASUITE]: "suite" });
      expect(kinds(form.values[TIQR_REG_SERVER]())).toEqual(["required"]);
      expect(kinds(form.values[TIQR_LOGO_URL]())).toEqual(["required"]);
      expect(kinds(form.values[TIQR_INFO_URL]())).toEqual([]);
      expect(kinds(form.values[TIQR_OCRASUITE]())).toEqual([]);
    });

    it("requires the Yubico API client ID and key together, not the URL", () => {
      const { form } = createTokenTypeConfigForm({ [YUBICO_ID]: "12345" });
      expect(kinds(form.values[YUBICO_SECRET]())).toEqual(["required"]);
      expect(kinds(form.values[YUBICO_URL]())).toEqual([]);
      expect(form().valid()).toBe(false);
    });

    it("is valid for Yubico credentials without a URL and for a URL without credentials", () => {
      expect(
        createTokenTypeConfigForm({ [YUBICO_ID]: "12345", [YUBICO_SECRET]: "key" })
          .form()
          .valid()
      ).toBe(true);
      expect(
        createTokenTypeConfigForm({ [YUBICO_URL]: "https://api.yubico.com" })
          .form()
          .valid()
      ).toBe(true);
    });

    it("treats whitespace as empty", () => {
      const { form } = createTokenTypeConfigForm({ [YUBICO_ID]: "  ", [YUBICO_SECRET]: "key" });
      expect(kinds(form.values[YUBICO_ID]())).toEqual(["required"]);
    });

    it("applies the rules when an entry is filled after the form exists", () => {
      const { form, model } = createTokenTypeConfigForm();
      model.update((current) => ({ ...current, values: { ...current.values, [TIQR_OCRASUITE]: "suite" } }));
      expect(form().valid()).toBe(false);
      model.update((current) => ({ ...current, values: { ...current.values, [TIQR_OCRASUITE]: "" } }));
      expect(form().valid()).toBe(true);
    });

    describe("questionnaire", () => {
      it("does not require the number of answers once a question exists, the backend defaults it", () => {
        const { form } = createTokenTypeConfigForm({ "question.question.0": "Q" });
        expect(kinds(form.values[QUESTION_NUMBER_OF_ANSWERS]())).toEqual([]);
        expect(form().valid()).toBe(true);
      });

      it("is valid when the number of answers and a question are filled", () => {
        const { form } = createTokenTypeConfigForm({ [QUESTION_NUMBER_OF_ANSWERS]: "2", "question.question.0": "Q" });
        expect(form().valid()).toBe(true);
      });

      it("accepts a whole number and rejects a sign, a decimal point and an exponent", () => {
        const check = (value: string) =>
          kinds(
            createTokenTypeConfigForm({ [QUESTION_NUMBER_OF_ANSWERS]: value }).form.values[QUESTION_NUMBER_OF_ANSWERS]()
          );
        expect(check("3")).toEqual([]);
        expect(check("-1")).toEqual(["pattern"]);
        expect(check("1.5")).toEqual(["pattern"]);
        expect(check("1e3")).toEqual(["pattern"]);
      });

      it("requires text in every question slot", () => {
        const { form } = createTokenTypeConfigForm({
          [QUESTION_NUMBER_OF_ANSWERS]: "2",
          "question.question.0": "Q",
          "question.question.1": ""
        });
        expect(kinds(form.values["question.question.0"]())).toEqual([]);
        expect(kinds(form.values["question.question.1"]())).toEqual(["required"]);
        expect(form().valid()).toBe(false);
      });

      it("rejects a question made of whitespace", () => {
        const { form } = createTokenTypeConfigForm({ [QUESTION_NUMBER_OF_ANSWERS]: "1", "question.question.0": "  " });
        expect(kinds(form.values["question.question.0"]())).toEqual(["required"]);
      });
    });
  });
});
