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
import { Component, computed, effect, inject, input, output } from "@angular/core";
import { MatButton } from "@angular/material/button";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { EnrollmentSecretComponent } from "@components/token/token-enrollment/token-enrollment-data/enrollment-secret/enrollment-secret.component";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { downloadBlob } from "@utils/download.utils";
import { SavedValues } from "@components/token/token-enrollment/token-enrollment-data/saved-values";

@Component({
  selector: "app-certificate-data",
  standalone: true,
  imports: [
    MatAccordion,
    MatButton,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatIcon,
    CopyButtonComponent,
    EnrollmentSecretComponent
  ],
  templateUrl: "./certificate-data.component.html",
  styleUrl: "./certificate-data.component.scss"
})
export class CertificateDataComponent {
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  serial = input<string>("");
  /** The issued certificate, PEM encoded. */
  certificate = input<string>("");
  /** The PKCS#12 container holding the private key, base64 encoded. */
  pkcs12 = input<string>("");
  /**
   * The passphrase of the container. The server returns it only in the enrollment response
   * and never stores it, so it can be shown exactly once. It is absent whenever the token
   * PIN was used as the passphrase instead.
   */
  pkcs12Password = input<string>("");
  rolloutState = input<string>("");
  /**
   * True while this shows an enrollment response. Only there does a missing passphrase mean
   * that the token PIN was used instead: the server never stores the generated passphrase, so
   * the token details cannot tell a PIN-encrypted container from one whose passphrase is lost.
   */
  fromEnrollment = input<boolean>(false);
  // Asks to save the passphrase now; the wizard asks only when leaving.
  saveHint = input<boolean>(true);

  // What has not been downloaded or saved yet; the wizard asks before it leaves.
  unsavedDataChange = output<string>();
  // What closing would lose for good, so the dialog asks first. Only the passphrase; the files stay in the details.
  closeConfirmationChange = output<string>();

  protected readonly isPending = computed(() => this.rolloutState() === "pending");
  protected readonly isDenied = computed(() => this.rolloutState() === "denied");
  protected readonly isFailed = computed(() => this.rolloutState() === "failed");

  // Downloaded files, the shown certificate and the revealed or copied passphrase; hiding again does not undo that.
  private readonly saved = new SavedValues();
  // Containers whose base64 does not decode hold nothing to rescue, so they are not asked for.
  private readonly unusablePkcs12 = new SavedValues();
  private readonly passwordAcknowledged = computed(() => this.saved.has(`passphrase:${this.pkcs12Password()}`));
  private readonly certificateDownloaded = computed(() => this.saved.has(`certificate:${this.certificate()}`));
  private readonly pkcs12Downloaded = computed(() => this.saved.has(`pkcs12:${this.pkcs12()}`));
  private readonly pkcs12Unusable = computed(() => this.unusablePkcs12.has(this.pkcs12()));

  protected readonly passphraseLabel = $localize`:@@token.passphrase:Passphrase`;
  protected readonly passphraseHint = $localize`:@@token.pkcs12PasswordOnce:Save the passphrase of the PKCS#12 container now. It is shown here only once and cannot be retrieved again.`;

  protected readonly unsavedData = computed(() => {
    const pending: string[] = [];
    if (this.certificate() && !this.certificateDownloaded()) {
      pending.push($localize`:@@token.pendingCertificateDownload:Download the certificate.`);
    }
    if (this.pkcs12() && !this.pkcs12Downloaded() && !this.pkcs12Unusable()) {
      pending.push($localize`:@@token.pendingPkcs12Download:Download the PKCS#12 file.`);
    }
    if (this.pkcs12Password() && !this.passwordAcknowledged()) {
      pending.push($localize`:@@token.pendingPassphrase:Show or copy the passphrase.`);
    }
    if (pending.length === 0) {
      return "";
    }
    return pending.join(" ");
  });

  protected readonly closeConfirmation = computed(() =>
    this.pkcs12Password() && !this.passwordAcknowledged()
      ? $localize`:@@token.closeLosesPassphrase:The passphrase of the PKCS#12 container is shown only once. If you close this dialog now, it cannot be retrieved again.`
      : ""
  );

  constructor() {
    effect(() => this.unsavedDataChange.emit(this.unsavedData()));
    effect(() => this.closeConfirmationChange.emit(this.closeConfirmation()));
  }

  acknowledgePassword(): void {
    this.saved.add(`passphrase:${this.pkcs12Password()}`);
  }

  downloadCertificate(): void {
    downloadBlob(new Blob([this.certificate()], { type: "application/x-pem-file" }), `${this.baseName()}.pem`);
    this.saved.add(`certificate:${this.certificate()}`);
  }

  onCertificateShown(): void {
    this.saved.add(`certificate:${this.certificate()}`);
  }

  downloadPkcs12(): void {
    let binary: ArrayBuffer;
    try {
      binary = this.decodeBase64(this.pkcs12());
    } catch {
      this.notificationService.error(
        $localize`:@@token.failedPkcs12Download:The PKCS#12 container of this token is damaged and cannot be downloaded.`
      );
      this.unusablePkcs12.add(this.pkcs12());
      return;
    }
    downloadBlob(new Blob([binary], { type: "application/x-pkcs12" }), `${this.baseName()}.p12`);
    this.saved.add(`pkcs12:${this.pkcs12()}`);
  }

  private baseName(): string {
    return this.serial() || "certificate";
  }

  private decodeBase64(value: string): ArrayBuffer {
    const characters = atob(value);
    const buffer = new ArrayBuffer(characters.length);
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < characters.length; i++) {
      bytes[i] = characters.charCodeAt(i);
    }
    return buffer;
  }
}
