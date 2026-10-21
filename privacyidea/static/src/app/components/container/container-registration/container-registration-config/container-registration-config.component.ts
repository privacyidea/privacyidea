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
import { Component, input } from "@angular/core";
import { applyWhen, disabled, FieldTree, FormField, required, SchemaPathTree, validate } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatHint, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { ERR, mustEqual } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

/** The passphrase settings of a container registration. */
export interface ContainerRegistrationModel {
  prompt: string;
  response: string;
  repeat: string;
  store: boolean;
}

/** Error kind of a repeated passphrase response that differs from the response. */
export const PASSPHRASE_MISMATCH = "passphraseMismatch";

export const DEFAULT_PASSPHRASE_PROMPT = "Please enter your user store passphrase.";

export function emptyRegistration(): ContainerRegistrationModel {
  return { prompt: "", response: "", repeat: "", store: false };
}

export interface ContainerRegistrationRulesOptions {
  /** The current registration value, read inside the validators so they re-run when it changes. */
  value: () => ContainerRegistrationModel;
  /** The passphrase rules apply only while this returns true, for example while a QR code is generated. */
  active?: () => boolean;
  /** The user store passphrase can only be validated for a container that has an owner. */
  hasOwner: () => boolean;
}

/**
 * Rules of the registration passphrase settings.
 * - Validating against the user store needs no passphrase response, so the response and its repetition are disabled.
 * - Otherwise a prompt needs a response that the repetition equals, and a response or repetition needs a prompt.
 */
export function registrationRules(
  path: SchemaPathTree<ContainerRegistrationModel>,
  options: ContainerRegistrationRulesOptions
) {
  const { value, hasOwner } = options;
  const active = options.active ?? (() => true);
  disabled(path.store, () => !hasOwner());
  disabled(path.response, () => value().store);
  disabled(path.repeat, () => value().store);
  applyWhen(
    path,
    () => active() && !value().store,
    (p) => {
      validate(p.prompt, () =>
        (value().response || value().repeat) && !value().prompt ? [{ kind: ERR.required }] : []
      );
      required(p.response, { when: () => !!value().prompt });
      mustEqual(p.repeat, () => value().response, PASSPHRASE_MISMATCH);
    }
  );
}

@Component({
  selector: "app-container-registration-config",
  templateUrl: "./container-registration-config.component.html",
  imports: [
    FormField,
    MatFormField,
    MatInput,
    MatHint,
    MatError,
    MatLabel,
    MatCheckbox,
    MatIconModule,
    MatButtonModule,
    MatSuffix
  ]
})
export class ContainerRegistrationConfigComponent {
  registration = input.required<FieldTree<ContainerRegistrationModel>>();

  protected readonly hasError = hasError;
  protected readonly ERR = ERR;
  protected readonly PASSPHRASE_MISMATCH = PASSPHRASE_MISMATCH;

  showPassphrase = false;
  showRepeatPassphrase = false;

  toggleShowPassphrase() {
    this.showPassphrase = !this.showPassphrase;
  }

  onUserStorePassphraseChange() {
    const registration = this.registration();
    if (registration.store().value()) {
      registration.response().value.set("");
      registration.repeat().value.set("");
      if (!registration.prompt().value()) {
        registration.prompt().value.set(DEFAULT_PASSPHRASE_PROMPT);
      }
    }
  }
}
