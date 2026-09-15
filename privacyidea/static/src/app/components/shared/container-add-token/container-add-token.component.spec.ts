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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatAutocomplete } from "@angular/material/autocomplete";
import { MatCheckbox, MatCheckboxChange } from "@angular/material/checkbox";
import { MatPaginator } from "@angular/material/paginator";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { TokenService } from "@services/token/token.service";
import { MockAuthService, MockContainerService, MockTokenService } from "@testing/mock-services";
import { By } from "@angular/platform-browser";
import { ContainerAddTokenComponent } from "./container-add-token.component";

describe("ContainerAddTokenComponent", () => {
  let fixture: ComponentFixture<ContainerAddTokenComponent>;
  let component: ContainerAddTokenComponent;
  let authService: MockAuthService;
  let containerService: MockContainerService;
  let tokenService: MockTokenService;

  const checkbox = () => fixture.debugElement.query(By.directive(MatCheckbox))?.componentInstance as MatCheckbox;
  const hint = () => fixture.nativeElement.querySelector("mat-hint") as HTMLElement | null;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerAddTokenComponent],
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["container_add_token"] });
    tokenService.showOnlyTokenInContainer.set(false);

    fixture = TestBed.createComponent(ContainerAddTokenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("renders the positively-phrased checkbox label", () => {
    expect(fixture.nativeElement.textContent).toContain("Include tokens that are in a container");
  });

  it("reflects the token service showOnlyTokenInContainer state in the checkbox", () => {
    expect(checkbox().checked).toBe(false);

    tokenService.showOnlyTokenInContainer.set(true);
    fixture.detectChanges();

    expect(checkbox().checked).toBe(true);
  });

  it("writes the checkbox change back to the token service", () => {
    checkbox().change.emit({ source: checkbox(), checked: true } as MatCheckboxChange);
    fixture.detectChanges();
    expect(tokenService.showOnlyTokenInContainer()).toBe(true);

    checkbox().change.emit({ source: checkbox(), checked: false } as MatCheckboxChange);
    fixture.detectChanges();
    expect(tokenService.showOnlyTokenInContainer()).toBe(false);
  });

  it("shows the move-token hint only while tokens in a container are included", () => {
    expect(hint()).toBeNull();

    tokenService.showOnlyTokenInContainer.set(true);
    fixture.detectChanges();

    expect(hint()).not.toBeNull();
    expect(hint()?.textContent).toContain("removes it from its previous container");
  });

  const openPanel = () => {
    const autocomplete = fixture.debugElement.query(By.directive(MatAutocomplete)).componentInstance as MatAutocomplete;
    autocomplete.opened.emit();
  };

  it("filters the token list by the token types of the container when the panel opens", () => {
    containerService.supportedTokenTypes.set(["hotp", "webauthn"]);

    openPanel();

    expect(tokenService.activeFilter().hiddenFilterMap.get("type_list")).toBe("hotp,webauthn");
  });

  it("keeps a typed filter when applying the token type filter", () => {
    containerService.supportedTokenTypes.set(["hotp", "webauthn"]);
    tokenService.activeFilter.set(new FilterValue({ value: "serial: OTP" }));

    openPanel();

    expect(tokenService.activeFilter().filterString).toBe("serial: OTP");
    expect(tokenService.activeFilter().hiddenFilterMap.get("type_list")).toBe("hotp,webauthn");
  });

  it("removes the type_list entry when the container supports no known token types", () => {
    tokenService.activeFilter.set(new FilterValue().updateHiddenEntry("type_list", "hotp"));
    containerService.supportedTokenTypes.set([]);

    openPanel();

    expect(tokenService.activeFilter().hiddenFilterMap.has("type_list")).toBe(false);
  });

  it("re-applies the token type filter after the filter was cleared", () => {
    tokenService.clearFilter.mockImplementation(() => tokenService.activeFilter.set(new FilterValue()));
    containerService.supportedTokenTypes.set(["hotp", "webauthn"]);
    openPanel();
    tokenService.activeFilter.set(tokenService.activeFilter().copyWith({ value: "serial: OTP" }));

    fixture.debugElement.query(By.directive(ClearableInputComponent)).componentInstance.clearButtonClick.emit();

    expect(tokenService.clearFilter).toHaveBeenCalled();
    expect(tokenService.activeFilter().filterString).toBe("");
    expect(tokenService.activeFilter().hiddenFilterMap.get("type_list")).toBe("hotp,webauthn");
  });

  it("renders the paginator next to the filter input and writes page events to the token service", () => {
    tokenService.tokenResourceValue.set({ count: 22, current: 1, tokens: [] });
    fixture.detectChanges();

    const paginator = fixture.debugElement.query(By.directive(MatPaginator));
    expect(paginator.nativeElement.closest(".mat-mdc-form-field-icon-suffix")).not.toBeNull();

    paginator.componentInstance.page.emit({ pageIndex: 1, pageSize: 5, length: 22 });

    expect(tokenService.eventPageSize()).toBe(5);
    expect(tokenService.pageIndex()).toBe(1);
  });

  it("does not render the panel when container_add_token is not allowed", () => {
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.directive(MatCheckbox))).toBeNull();
  });
});
