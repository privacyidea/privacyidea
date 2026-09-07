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
import { Component, computed, effect, inject, input, output, signal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";

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
    CopyButtonComponent
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
   * Names what still has to be saved before the dialog may be closed, or an empty string once
   * nothing is left. The dialog disables its close button while this is set and shows it as
   * the button's tooltip.
   */
  closeBlockedReasonChange = output<string>();

  protected readonly isPending = computed(() => this.rolloutState() === "pending");
  protected readonly isDenied = computed(() => this.rolloutState() === "denied");
  protected readonly isFailed = computed(() => this.rolloutState() === "failed");

  protected readonly passwordVisible = signal(false);
  // Tracks that the passphrase was actually taken note of, either by revealing or by copying
  // it. Toggling it hidden again does not undo that.
  private readonly passwordAcknowledged = signal(false);
  private readonly certificateDownloaded = signal(false);
  private readonly pkcs12Downloaded = signal(false);
  // A container whose base64 does not decode holds nothing to rescue, so it must not be able
  // to lock the user inside the dialog.
  private readonly pkcs12Unusable = signal(false);

  protected readonly maskedPassword = computed(() => "\u2022".repeat(this.pkcs12Password().length));

  protected readonly closeBlockedReason = computed(() => {
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
    return pending.join("\n");
  });

  constructor() {
    effect(() => this.closeBlockedReasonChange.emit(this.closeBlockedReason()));
  }

  /** Accessible name of the icon-only toggle button. */
  protected readonly passwordToggleLabel = computed(() =>
    this.passwordVisible()
      ? $localize`:@@token.hidePassphrase:Hide passphrase`
      : $localize`:@@token.showPassphrase:Show passphrase`
  );

  togglePasswordVisible(): void {
    const visible = !this.passwordVisible();
    this.passwordVisible.set(visible);
    if (visible) {
      this.acknowledgePassword();
    }
  }

  acknowledgePassword(): void {
    this.passwordAcknowledged.set(true);
  }

  downloadCertificate(): void {
    this.download(new Blob([this.certificate()], { type: "application/x-pem-file" }), `${this.baseName()}.pem`);
    this.certificateDownloaded.set(true);
  }

  downloadPkcs12(): void {
    let binary: ArrayBuffer;
    try {
      binary = this.decodeBase64(this.pkcs12());
    } catch {
      this.notificationService.error(
        $localize`:@@token.failedPkcs12Download:The PKCS#12 container of this token is damaged and cannot be downloaded.`
      );
      this.pkcs12Unusable.set(true);
      return;
    }
    this.download(new Blob([binary], { type: "application/x-pkcs12" }), `${this.baseName()}.p12`);
    this.pkcs12Downloaded.set(true);
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

  private download(blob: Blob, fileName: string): void {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    anchor.click();
    window.URL.revokeObjectURL(url);
  }
}
