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

import { Component, computed, effect, inject, OnDestroy, signal, untracked } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { disabled, form, FormField, max, min, pattern, required, validate } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatDivider } from "@angular/material/list";
import { MatSelectModule } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { TooltipAriaLabelDirective } from "@components/shared/directives/tooltip-aria-label.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { ERR, markRequired } from "@utils/form-rules.utils";
import { clearField, hasError } from "@utils/form-state.utils";
import { reservedNames } from "@utils/reserved-names.utils";
import {
  encodesPlaceholderValues,
  Webhook,
  WEBHOOK_AUTH_TYPES,
  WEBHOOK_CONTENT_TYPES,
  WEBHOOK_HTTP_METHODS,
  WebhookAuthType,
  WebhookHttpMethod,
  WebhookService,
  WebhookServiceInterface,
  WebhookTestResult
} from "@services/webhook/webhook.service";

/**
 * One row of the header table. `secret` is the stored encryption flag; for a secret header the
 * backend returns `__CENSORED__` as the value and reads it back as "keep what is stored", so a
 * round-trip through this form neither reveals nor rewrites the secret.
 */
interface HeaderRow {
  key: string;
  value: string;
  secret: boolean;
  /**
   * The name this row was loaded under, absent for a row the admin added. When it differs from
   * `key` the row was renamed, and the save says so - otherwise the server sees a delete plus a
   * create and a secret header's value is lost, since this form only ever holds the placeholder
   * for it.
   */
  originalKey?: string;
}

/**
 * Characters of an HTTP header name: a `token` of RFC 9110, section 5.6.2. The server refuses a header
 * with any other character, so the form does it first.
 */
const HEADER_NAME_PATTERN = /^[!#$%&'*+.^_`|~0-9A-Za-z-]+$/;

/** Why a row of the header table cannot be saved. */
type HeaderNameError = "required" | "invalid" | "duplicate";

/**
 * A header value that the server accepts: empty, or no leading whitespace and no line break. The server checks it
 * because requests refuses any other value with an error that quotes the value, which can be a secret.
 */
const HEADER_VALUE_PATTERN = /^(\S[^\r\n]*)?$/;

/** The server refuses a timeout that is not a whole number of seconds in this range. */
const TIMEOUT_MIN_SECONDS = 1;
const TIMEOUT_MAX_SECONDS = 3600;

/** Error kinds of the rules in this form that the shared `ERR` kinds do not cover. */
const WEBHOOK_ERR = {
  wholeNumber: "wholeNumber",
  headerAuthNeedsHeader: "headerAuthNeedsHeader",
  notMimeType: "notMimeType"
} as const;

interface WebhookFormModel {
  identifier: string;
  description: string;
  url: string;
  http_method: WebhookHttpMethod;
  content_type: string;
  default_payload: string;
  auth_type: WebhookAuthType;
  username: string;
  password: string;
  verify_tls: boolean;
  tls_ca_bundle: string;
  client_certificate: string;
  client_key: string;
  client_key_password: string;
  http_proxy: string;
  https_proxy: string;
  // `number | null`: a number input writes null to the model while it is empty.
  timeout: number | null;
  encode_values: boolean;
}

const EMPTY_WEBHOOK_FORM: WebhookFormModel = {
  identifier: "",
  description: "",
  url: "",
  http_method: "POST",
  content_type: "application/json",
  default_payload: "",
  auth_type: "none",
  username: "",
  password: "",
  // Mirrors the server default: verification is on unless an admin deliberately turns it off.
  verify_tls: true,
  tls_ca_bundle: "",
  client_certificate: "",
  client_key: "",
  client_key_password: "",
  http_proxy: "",
  https_proxy: "",
  timeout: 3,
  // Mirrors the server default for a new webhook.
  encode_values: true
};

@Component({
  selector: "app-new-webhook",
  standalone: true,
  imports: [
    FormField,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatTooltip,
    TooltipAriaLabelDirective,
    ClearableInputComponent,
    MatDivider,
    StickyHeaderDirective
  ],
  templateUrl: "./new-webhook.component.html",
  styleUrl: "./new-webhook.component.scss"
})
export class NewWebhookComponent implements OnDestroy {
  isEditMode = signal(false);
  isTesting = signal(false);
  testResult = signal<WebhookTestResult | null>(null);
  webhookModel = signal<WebhookFormModel>({ ...EMPTY_WEBHOOK_FORM });
  /**
   * The headers live outside the validated form: the signal-forms API validates a fixed set of
   * fields, while this is a table whose rows come and go. Its own dirty flag is folded into
   * `hasChanges` so the unsaved-changes guard still sees a header-only edit.
   */
  headers = signal<HeaderRow[]>([]);
  webhookForm = form(this.webhookModel, (f) => {
    required(f.identifier);
    pattern(f.identifier, /^[a-zA-Z0-9._-]*$/);
    // The pattern lets "." and ".." through, and encodeURIComponent() leaves them as they are.
    // A browser removes those dot segments while resolving the save URL, so a POST to
    // /webhook/. goes to /webhook/ and /webhook/.. to /, and the webhook is never created -
    // with Save looking perfectly enabled. Same rule as the SMTP, RADIUS and privacyIDEA server
    // editors. The routes need no reserved word of their own: the test endpoint is
    // /webhook/<identifier>/test, so an identifier cannot collide with it.
    reservedNames(f.identifier, [".", ".."]);
    // POST /webhook/<identifier> creates or updates, so creating a webhook under a taken identifier would overwrite
    // the stored one.
    validate(f.identifier, () => (this.identifierConflict() ? { kind: ERR.nameTaken } : null));
    required(f.url);
    // The same rule set_webhook() enforces; catching it here saves a round-trip to a 400.
    pattern(f.url, /^https?:\/\/.+/i);
    required(f.timeout);
    min(f.timeout, TIMEOUT_MIN_SECONDS);
    max(f.timeout, TIMEOUT_MAX_SECONDS);
    validate(f.timeout, ({ value }) => {
      const timeout = value();
      return timeout !== null && !Number.isInteger(timeout) ? { kind: WEBHOOK_ERR.wholeNumber } : null;
    });
    // The server refuses a content type without a "/", that is, one that is not a MIME type. An empty value is
    // refused too: the server would store application/json then, and the field would not show it.
    validate(f.content_type, ({ value }) => (value().includes("/") ? null : { kind: WEBHOOK_ERR.notMimeType }));
    // The server refuses basic authentication without a username.
    validate(f.username, ({ value }) =>
      this.webhookModel().auth_type === "basic" && !value().trim()
        ? {
            kind: "required",
            message: $localize`:@@webhook.basicAuthNeedsUsername:Basic authentication needs a username.`
          }
        : null
    );
    markRequired(f.username, () => this.webhookModel().auth_type === "basic");
    // It also refuses mTLS without a client certificate, and header authentication without a header.
    validate(f.client_certificate, ({ value }) =>
      this.webhookModel().auth_type === "mtls" && !value().trim() ? { kind: ERR.required } : null
    );
    markRequired(f.client_certificate, () => this.webhookModel().auth_type === "mtls");
    // The headers are not part of this form, so the rule sits on the field that asks for them.
    validate(f.auth_type, ({ value }) =>
      value() === "header" && this.namedHeaderCount() === 0 ? { kind: WEBHOOK_ERR.headerAuthNeedsHeader } : null
    );
    disabled(f.identifier, () => this.isEditMode());
    // Only consulted while verification is on, so it is not offered while it is off.
    disabled(f.tls_ca_bundle, () => !this.webhookModel().verify_tls);
  });
  readonly showBasicAuth = computed(() => this.webhookModel().auth_type === "basic");
  readonly showMtls = computed(() => this.webhookModel().auth_type === "mtls");
  readonly showHeaderAuthNote = computed(() => this.webhookModel().auth_type === "header");
  readonly showEncodeValues = computed(() => encodesPlaceholderValues(this.webhookModel().content_type));
  /** A fraction, a value below the minimum and one above the maximum share one message. */
  readonly timeoutOutOfRange = computed(() =>
    [WEBHOOK_ERR.wholeNumber, ERR.min, ERR.max].some((kind) => hasError(this.webhookForm.timeout, kind))
  );
  /**
   * One entry per row of the header table: why the row cannot be saved, or null. A row without a name
   * and without a value is an unfinished row and is left out of the save, so it is no error. Names
   * compare case-insensitively, as HTTP does: the server would store "X-Key" and "x-key" as two
   * headers and send whichever comes last.
   */
  readonly headerNameErrors = computed<(HeaderNameError | null)[]>(() => {
    const rows = this.headers();
    const counts = new Map<string, number>();
    for (const row of rows) {
      const name = row.key.trim().toLowerCase();
      if (name) {
        counts.set(name, (counts.get(name) ?? 0) + 1);
      }
    }
    return rows.map((row) => {
      const name = row.key.trim();
      if (!name) {
        return row.value ? "required" : null;
      }
      if (!HEADER_NAME_PATTERN.test(name)) {
        return "invalid";
      }
      return (counts.get(name.toLowerCase()) ?? 0) > 1 ? "duplicate" : null;
    });
  });
  /** One entry per row of the header table: true when the server would refuse the value of the row. */
  readonly headerValueErrors = computed<boolean[]>(() =>
    this.headers().map((row) => !HEADER_VALUE_PATTERN.test(row.value))
  );
  readonly headersValid = computed(
    () =>
      this.headerNameErrors().every((error) => error === null) && this.headerValueErrors().every((invalid) => !invalid)
  );
  protected readonly webhookService: WebhookServiceInterface = inject(WebhookService);
  /**
   * In create mode, the stored webhook that already has the identifier in the form. The comparison ignores case:
   * MySQL and MariaDB compare the identifier without case in their default collation, so there a save under
   * "Siem" finds and overwrites the stored webhook "siem". PostgreSQL stores the two as separate webhooks, but the
   * editor cannot tell which database the server uses, so it refuses the pair on every database. In edit mode the
   * identifier is the one being edited and cannot change.
   */
  readonly identifierConflict = computed<Webhook | undefined>(() => {
    const identifier = this.webhookModel().identifier.toLowerCase();
    if (this.isEditMode() || !identifier) {
      return undefined;
    }
    return this.webhookService.webhooks().find((webhook) => webhook.identifier.toLowerCase() === identifier);
  });
  protected readonly authTypes = WEBHOOK_AUTH_TYPES;
  protected readonly httpMethods = WEBHOOK_HTTP_METHODS;
  protected readonly contentTypes = WEBHOOK_CONTENT_TYPES;
  protected readonly ERR = ERR;
  protected readonly WEBHOOK_ERR = WEBHOOK_ERR;
  /** The characters other than letters and digits that HEADER_NAME_PATTERN allows, for its error message. */
  protected readonly headerNameSpecialCharacters = "! # $ % & ' * + - . ^ _ ` | ~";
  protected readonly hasError = hasError;
  protected readonly clearField = clearField;
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  /** POST, DELETE and the test call of /webhook/ all require webhook_write. */
  protected readonly canWrite = computed(() => this.authService.actionAllowed("webhook_write"));
  protected data: Webhook | null = null;
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);
  private editIdentifier: string | null = null;
  private headersDirty = signal(false);
  /** The rows of the header table that are sent, that is, the rows with a name. */
  private readonly namedHeaderCount = computed(() => this.headers().filter((row) => row.key.trim()).length);
  /**
   * The test endpoint fires the *stored* definition, not what is on screen, so testing an unsaved
   * form would report on something else than what is being edited.
   */
  readonly canTest = computed(
    () => this.canWrite() && this.isEditMode() && !this.headersDirty() && !this.webhookForm().dirty()
  );

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const identifier = params.get("identifier");
      if (identifier) {
        this.isEditMode.set(true);
        this.editIdentifier = identifier;
        this.data = this.webhookService.webhooks().find((w) => w.identifier === identifier) ?? null;
      } else {
        this.isEditMode.set(false);
        this.editIdentifier = null;
        this.data = null;
      }
      this.loadData(this.data);
    });

    // Save is blocked for a taken identifier, so the reason shows at once and not only after the field loses focus.
    effect(() => {
      if (this.identifierConflict()) {
        this.webhookForm.identifier().markAsTouched();
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const webhooks = this.webhookService.webhooks();
      if (
        this.isEditMode() &&
        this.editIdentifier &&
        untracked(() => !this.webhookForm().dirty() && !this.headersDirty())
      ) {
        const found = webhooks.find((w) => w.identifier === this.editIdentifier);
        if (found) {
          this.data = found;
          this.loadData(this.data);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return this.webhookForm().dirty() || this.headersDirty();
  }

  get canSave(): boolean {
    if (!this.canWrite()) {
      return false;
    }
    // In edit mode the form only describes the stored definition once the list has arrived. Until
    // then it holds the empty defaults, and saving those would POST them over a real webhook -
    // clearing its URL, auth and headers. The form does not catch it by itself: the identifier is
    // `disabled()` in edit mode, and a disabled field skips its own `required` validator.
    if (this.isEditMode() && !this.data) {
      return false;
    }
    return this.webhookForm().valid() && this.headersValid();
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  addHeader(): void {
    this.headers.update((rows) => [...rows, { key: "", value: "", secret: false }]);
    this.headersDirty.set(true);
  }

  removeHeader(index: number): void {
    this.headers.update((rows) => rows.filter((_, i) => i !== index));
    this.headersDirty.set(true);
  }

  updateHeader(index: number, patch: Partial<HeaderRow>): void {
    this.headers.update((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
    this.headersDirty.set(true);
  }

  async save(): Promise<boolean> {
    if (!this.canSave) {
      return false;
    }
    const model = this.webhookModel();
    // A header with no name is an unfinished row, not a header to send. canSave() refuses a row with
    // a value but no name, so only a row without both is left out here.
    const rows = this.headers().filter((row) => row.key.trim());
    const webhook: Webhook = {
      ...model,
      // The route is what says which webhook is being edited; the model's copy only mirrors it,
      // and mirrors it as "" until the definition has loaded. Posting that would address
      // /webhook/ instead of /webhook/<identifier>.
      identifier: this.editIdentifier ?? model.identifier,
      timeout: Number(model.timeout),
      headers: Object.fromEntries(rows.map((row) => [row.key.trim(), row.value])),
      secret_headers: rows.filter((row) => row.secret).map((row) => row.key.trim())
    };

    // A row that was loaded under another name was renamed. The server addresses a header by its
    // name, so it has to be told; otherwise the rename is a delete plus a create and a secret
    // header's value is gone, because this form only ever held the placeholder for it.
    const renames = Object.fromEntries(
      this.headers()
        .filter((row) => row.originalKey && row.key.trim() && row.originalKey !== row.key.trim())
        .map((row) => [row.key.trim(), row.originalKey as string])
    );

    try {
      await this.webhookService.postWebhook(webhook, renames);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Fire the stored webhook once and show what the endpoint answered. The request really goes out,
   * so a test against a production endpoint has real side effects.
   */
  async test(): Promise<void> {
    if (!this.canTest() || !this.editIdentifier) {
      return;
    }
    this.isTesting.set(true);
    this.testResult.set(await this.webhookService.testWebhook(this.editIdentifier));
    this.isTesting.set(false);
  }

  onCancel(): void {
    if (this.hasChanges) {
      this.dialogService
        .openDialog({
          component: SaveAndExitDialogComponent,
          data: {
            allowSaveExit: true,
            saveExitDisabled: !this.canSave
          }
        })
        .afterClosed()
        .subscribe(async (result) => {
          if (result === "discard") {
            this.pendingChangesService.clearAllRegistrations();
            this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS);
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            const success = await this.pendingChangesService.save();
            if (!success) return;
            this.pendingChangesService.clearAllRegistrations();
            this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS);
          }
        });
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS);
    }
  }

  private loadData(data: Webhook | null): void {
    this.webhookModel.set({
      identifier: data?.identifier || "",
      description: data?.description || "",
      url: data?.url || "",
      http_method: data?.http_method || "POST",
      content_type: data?.content_type || "application/json",
      default_payload: data?.default_payload || "",
      auth_type: data?.auth_type || "none",
      username: data?.username || "",
      password: data?.password || "",
      verify_tls: data?.verify_tls ?? true,
      tls_ca_bundle: data?.tls_ca_bundle || "",
      client_certificate: data?.client_certificate || "",
      client_key: data?.client_key || "",
      client_key_password: data?.client_key_password || "",
      http_proxy: data?.http_proxy || "",
      https_proxy: data?.https_proxy || "",
      timeout: data?.timeout ?? 3,
      encode_values: data?.encode_values ?? true
    });
    const secretHeaders = data?.secret_headers ?? [];
    this.headers.set(
      Object.entries(data?.headers ?? {}).map(([key, value]) => ({
        key,
        value,
        secret: secretHeaders.includes(key),
        originalKey: key
      }))
    );
    this.headersDirty.set(false);
    this.testResult.set(null);
    this.webhookForm().reset();
  }
}
