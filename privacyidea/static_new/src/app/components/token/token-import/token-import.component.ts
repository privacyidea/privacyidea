/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, computed, ElementRef, inject, Renderer2, signal, ViewChild } from "@angular/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatOption, MatSelect } from "@angular/material/select";
import {
  AbstractControl,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators
} from "@angular/forms";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { MatButton, MatIconButton } from "@angular/material/button";
import { NgClass } from "@angular/common";
import { MatInput } from "@angular/material/input";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-token-import",
  templateUrl: "./token-import.component.html",
  styleUrl: "./token-import.component.scss",
  imports: [
    MatFormField,
    MatSelect,
    FormsModule,
    MatOption,
    ScrollToTopDirective,
    MatLabel,
    MatButton,
    NgClass,
    MatInput,
    MatHint,
    MatIcon,
    MatIconButton,
    MatError,
    ReactiveFormsModule
  ]
})
export class TokenImportComponent {
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private observer!: IntersectionObserver;
  protected readonly renderer: Renderer2 = inject(Renderer2);

  fileTypes: Record<string, string> = {
    "OATH CSV": "CSV File for OATH Tokens",
    "Yubikey CSV": "CSV File for Yubikey Tokens",
    "pskc": "PSKC File",
    "aladdin-xml": "XML File from Aladdin or SafeNet"
  };
  fileType = signal<string>("OATH CSV");
  fileName = signal("");
  file: FormControl<string | Blob> = new FormControl("", { nonNullable: true, validators: [Validators.required] });
  preSharedKey = new FormControl("", this.preSharedKeyLength());
  pskPassword = signal("");
  pskValidationOptions: Record<string, string> = {
    "no_check": "Do not verify the authenticity",
    "check_fail_soft": "Skip tokens that can not be verified",
    "check_fail_hard": "Abort operation on unverifiable token"
  };
  pskValidation = signal("check_fail_hard");
  selectedRealms = signal<string[]>(
    this.realmService.defaultRealm() ? [this.realmService.defaultRealm()!] : []
  );
  inputForm = new FormGroup({
    file: this.file,
    preSharedKey: this.preSharedKey
  });

  preSharedKeyLength(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const validLength = [0, 32].includes(control.value.length);
      return validLength ? null : { invalidLength: { value: control.value } };
    };
  }

  @ViewChild("scrollContainer") scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild("stickyHeader") stickyHeader!: ElementRef<HTMLElement>;
  @ViewChild("stickySentinel") stickySentinel!: ElementRef<HTMLElement>;

  ngAfterViewInit(): void {
    if (!this.scrollContainer || !this.stickyHeader || !this.stickySentinel) {
      return;
    }

    const options = {
      root: this.scrollContainer.nativeElement,
      threshold: [0, 1]
    };

    this.observer = new IntersectionObserver(([entry]) => {
      if (!entry.rootBounds) return;

      const isSticky = entry.boundingClientRect.top < entry.rootBounds.top;

      if (isSticky) {
        this.renderer.addClass(this.stickyHeader.nativeElement, "is-sticky");
      } else {
        this.renderer.removeClass(this.stickyHeader.nativeElement, "is-sticky");
      }
    }, options);

    this.observer.observe(this.stickySentinel.nativeElement);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.file.setValue(input.files[0]);
      this.fileName.set(input.files[0].name);
    } else {
      this.fileName.set("");
    }
  }

  importTokens() {
    if (this.inputForm.valid) {
      const formData = new FormData();
      formData.append("file", this.file.value);
      formData.append("type", this.fileType());
      if (this.selectedRealms()) {
        formData.append("tokenrealms", this.selectedRealms().join(","));
      }
      if (this.fileType() === "pskc") {
        if (this.pskPassword()) {
          formData.append("password", this.pskPassword());
        }
        if (this.preSharedKey.value) {
          formData.append("psk", this.preSharedKey.value);
        }
        formData.append("pskcValidateMAC", this.pskValidation());
      }

      this.tokenService.importTokens(this.fileName(), formData).subscribe({
        next: (result) => {
          // Handle successful import, e.g., show a notification
          const success = result.result?.value?.n_imported || 0;
          const failed = result.result?.value?.n_not_imported || 0;
          const total = success + failed;
          this.notificationService.openSnackBar(success + "/" + total + " tokens imported successfully.");
        }
      });
    }
  }

  clearFileSelection() {
    this.file.setValue("");
    this.fileName.set("");
  }

  protected readonly Object = Object;
}
