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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { WritableSignal } from "@angular/core";
import { DetailsEditRegistry } from "@components/shared/details-shared/field-editing/details-edit-registry.service";
import { EditableField } from "@components/shared/details-shared/field-editing/editable-field";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { RealmService } from "@services/realm/realm.service";
import { TokenGroup, TokenGroups, TokenService } from "@services/token/token.service";
import { MockContainerService, MockContentService, MockRealmService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { mockTokenDetails } from "@testing/mock-token-details";
import { of } from "rxjs";
import { TokenDetailsAssignmentsComponent } from "./token-details-assignments.component";

interface AssignmentsFieldInternals {
  realmsField: EditableField;
  tokengroupField: EditableField;
  containerField: EditableField;
  realmOptions: () => { value: string; label: string; disabled: boolean }[];
  tokengroupSelectOptions: () => { value: string; label: string; disabled: boolean }[];
  tokengroupOptions: WritableSignal<string[]>;
  selectedTokengroup: WritableSignal<string[]>;
  str: (value: unknown) => string;
  removeContainer: () => void;
}

describe("TokenDetailsAssignmentsComponent", () => {
  let component: TokenDetailsAssignmentsComponent;
  let internals: AssignmentsFieldInternals;
  let fixture: ComponentFixture<TokenDetailsAssignmentsComponent>;
  let tokenService: MockTokenService;
  let realmService: MockRealmService;
  let containerService: MockContainerService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsAssignmentsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DetailsEditRegistry,
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsAssignmentsComponent);
    component = fixture.componentInstance;
    internals = component as unknown as AssignmentsFieldInternals;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    fixture.componentRef.setInput("tokenDetails", mockTokenDetails());
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("renders the realms, tokengroup and container rows", () => {
    // realms + tokengroup render a list display when not editing
    expect(fixture.nativeElement.querySelectorAll("app-details-list-display").length).toBe(2);
    // container row
    expect(fixture.nativeElement.querySelector(".container-serial-row")).toBeTruthy();

    const keys = Array.from(fixture.nativeElement.querySelectorAll<HTMLElement>(".detail-field-label")).map((el) =>
      el.textContent?.trim()
    );
    expect(keys).toEqual(["Token Realms", "Token Groups", "Container Serial"]);
  });

  it("computes realmOptions from realmService.realmOptions, disabling the current user realm", () => {
    realmService.realmOptions.set(["realm1", "realm2"]);
    fixture.componentRef.setInput("userRealm", "realm2");
    fixture.detectChanges();

    expect(internals.realmOptions()).toEqual([
      { value: "realm1", label: "realm1", disabled: false },
      { value: "realm2", label: "realm2", disabled: true }
    ]);
  });

  it("computes tokengroupSelectOptions from tokengroupOptions, disabling the current user realm", () => {
    internals.tokengroupOptions.set(["group1", "group2"]);
    fixture.componentRef.setInput("userRealm", "group2");
    fixture.detectChanges();

    expect(internals.tokengroupSelectOptions()).toEqual([
      { value: "group1", label: "group1", disabled: false },
      { value: "group2", label: "group2", disabled: true }
    ]);
  });

  it("realmsField.toggle() seeds selectedRealms from the token realms when entering edit mode", () => {
    fixture.componentRef.setInput("tokenDetails", mockTokenDetails({ realms: ["realmA", "realmB"] }));
    fixture.detectChanges();

    internals.realmsField.toggle();

    expect(internals.realmsField.isEditing()).toBe(true);
    expect(realmService.selectedRealms()).toEqual(["realmA", "realmB"]);
  });

  it("realmsField.cancel() restores selectedRealms from the token realms and leaves edit mode", () => {
    fixture.componentRef.setInput("tokenDetails", mockTokenDetails({ realms: ["realmA"] }));
    fixture.detectChanges();

    internals.realmsField.toggle();
    realmService.selectedRealms.set(["otherRealm"]);

    internals.realmsField.cancel();

    expect(realmService.selectedRealms()).toEqual(["realmA"]);
    expect(internals.realmsField.isEditing()).toBe(false);
  });

  it("realmsField.commit() persists the selected realms by token serial and reloads the token details", async () => {
    const tokenDetails = mockTokenDetails({ realms: ["realmA"], serial: "TOK-1" });
    fixture.componentRef.setInput("tokenDetails", tokenDetails);
    fixture.detectChanges();
    tokenService.setTokenRealm.mockReturnValue(of(MockPiResponse.fromValue(true)));

    internals.realmsField.toggle();
    realmService.selectedRealms.set(["realmB"]);

    await internals.realmsField.commit();

    expect(tokenService.setTokenRealm).toHaveBeenCalledWith("TOK-1", ["realmB"]);
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    expect(internals.realmsField.isEditing()).toBe(false);
  });

  it("tokengroupField.toggle() seeds selectedTokengroup and fetches tokengroups when none are loaded yet", () => {
    fixture.componentRef.setInput(
      "tokenDetails",
      mockTokenDetails({ tokengroup: ["group1"] as unknown as TokenGroup[] })
    );
    fixture.detectChanges();
    tokenService.getTokengroups.mockReturnValue(
      of(MockPiResponse.fromValue({ group1: [], group2: [] } as unknown as TokenGroups))
    );

    internals.tokengroupField.toggle();

    expect(internals.tokengroupField.isEditing()).toBe(true);
    expect(internals.selectedTokengroup()).toEqual(["group1"]);
    expect(tokenService.getTokengroups).toHaveBeenCalled();
    expect(internals.tokengroupOptions()).toEqual(["group1", "group2"]);
  });

  it("tokengroupField.toggle() does not refetch tokengroups when options are already loaded", () => {
    internals.tokengroupOptions.set(["existingGroup"]);
    fixture.componentRef.setInput(
      "tokenDetails",
      mockTokenDetails({ tokengroup: ["existingGroup"] as unknown as TokenGroup[] })
    );
    fixture.detectChanges();

    internals.tokengroupField.toggle();

    expect(tokenService.getTokengroups).not.toHaveBeenCalled();
    expect(internals.selectedTokengroup()).toEqual(["existingGroup"]);
    expect(internals.tokengroupOptions()).toEqual(["existingGroup"]);
  });

  it("tokengroupField.toggle() falls back to an empty tokengroup list when the response has no value", () => {
    tokenService.getTokengroups.mockReturnValue(
      of(MockPiResponse.fromValue<TokenGroups>(undefined as unknown as TokenGroups))
    );

    internals.tokengroupField.toggle();

    expect(internals.tokengroupOptions()).toEqual([]);
  });

  it("tokengroupField.cancel() restores selectedTokengroup from the token tokengroup and leaves edit mode", () => {
    fixture.componentRef.setInput(
      "tokenDetails",
      mockTokenDetails({ tokengroup: ["group1"] as unknown as TokenGroup[] })
    );
    fixture.detectChanges();
    tokenService.getTokengroups.mockReturnValue(of(MockPiResponse.fromValue({ group1: [] } as unknown as TokenGroups)));

    internals.tokengroupField.toggle();
    internals.selectedTokengroup.set(["otherGroup"]);

    internals.tokengroupField.cancel();

    expect(internals.selectedTokengroup()).toEqual(["group1"]);
    expect(internals.tokengroupField.isEditing()).toBe(false);
  });

  it("tokengroupField.commit() persists the selected tokengroup by token serial and reloads the token details", async () => {
    const tokenDetails = mockTokenDetails({ tokengroup: ["group1"] as unknown as TokenGroup[], serial: "TOK-2" });
    fixture.componentRef.setInput("tokenDetails", tokenDetails);
    fixture.detectChanges();
    tokenService.setTokengroup.mockReturnValue(of(MockPiResponse.fromValue(1)));
    tokenService.getTokengroups.mockReturnValue(of(MockPiResponse.fromValue({ group1: [] } as unknown as TokenGroups)));

    internals.tokengroupField.toggle();
    internals.selectedTokengroup.set(["group2"]);

    await internals.tokengroupField.commit();

    expect(tokenService.setTokengroup).toHaveBeenCalledWith("TOK-2", ["group2"]);
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    expect(internals.tokengroupField.isEditing()).toBe(false);
  });

  it("containerField.toggle() resets selectedContainerSerial when entering edit mode", () => {
    containerService.selectedContainerSerial.set("preset");

    internals.containerField.toggle();

    expect(internals.containerField.isEditing()).toBe(true);
    expect(containerService.selectedContainerSerial()).toBe("");
  });

  it("containerField.cancel() resets selectedContainerSerial and leaves edit mode", () => {
    internals.containerField.toggle();
    containerService.selectedContainerSerial.set("CONT-X");

    internals.containerField.cancel();

    expect(containerService.selectedContainerSerial()).toBe("");
    expect(internals.containerField.isEditing()).toBe(false);
  });

  it("containerField.commit() adds the token to the trimmed selected container and reloads the token details", async () => {
    const tokenDetails = mockTokenDetails({ serial: "TOK-3" });
    fixture.componentRef.setInput("tokenDetails", tokenDetails);
    fixture.detectChanges();

    internals.containerField.toggle();
    containerService.selectedContainerSerial.set(" CONT-9 ");

    await internals.containerField.commit();

    expect(containerService.addToken).toHaveBeenCalledWith("TOK-3", "CONT-9");
    expect(containerService.selectedContainerSerial()).toBe("CONT-9");
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    expect(internals.containerField.isEditing()).toBe(false);
  });

  it("containerField.commit() does not add a token when no container is selected", async () => {
    internals.containerField.toggle();
    containerService.selectedContainerSerial.set("   ");

    await internals.containerField.commit();

    expect(containerService.addToken).not.toHaveBeenCalled();
    expect(containerService.selectedContainerSerial()).toBe("");
  });

  it("containerField.commit() does not add a token when selectedContainerSerial is null", async () => {
    internals.containerField.toggle();
    containerService.selectedContainerSerial.set(null as unknown as string);

    await internals.containerField.commit();

    expect(containerService.addToken).not.toHaveBeenCalled();
    expect(containerService.selectedContainerSerial()).toBeNull();
  });

  it("removeContainer() does nothing when the token has no container", () => {
    fixture.componentRef.setInput("tokenDetails", mockTokenDetails({ container_serial: "" }));
    fixture.detectChanges();

    internals.removeContainer();

    expect(containerService.removeToken).not.toHaveBeenCalled();
  });

  it("removeContainer() removes the token from its container and reloads the token details", () => {
    const tokenDetails = mockTokenDetails({ container_serial: "CONT-5", serial: "TOK-4" });
    fixture.componentRef.setInput("tokenDetails", tokenDetails);
    fixture.detectChanges();
    containerService.selectedContainerSerial.set("CONT-5");

    internals.removeContainer();

    expect(containerService.removeToken).toHaveBeenCalledWith("TOK-4", "CONT-5");
    expect(containerService.selectedContainerSerial()).toBe("");
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
  });

  it("str() returns an empty string for null or undefined and stringifies other values", () => {
    expect(internals.str(null)).toBe("");
    expect(internals.str(undefined)).toBe("");
    expect(internals.str(123)).toBe("123");
    expect(internals.str("abc")).toBe("abc");
  });
});
