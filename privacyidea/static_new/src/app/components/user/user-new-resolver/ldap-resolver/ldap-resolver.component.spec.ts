import { ComponentFixture, TestBed } from "@angular/core/testing";
import { LdapResolverComponent } from "./ldap-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";
import { ResolverService } from "../../../../services/resolver/resolver.service";
import { MockResolverService } from "../../../../../testing/mock-services/mock-resolver-service";

describe("LdapResolverComponent", () => {
  let component: LdapResolverComponent;
  let componentRef: ComponentRef<LdapResolverComponent>;
  let fixture: ComponentFixture<LdapResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LdapResolverComponent, NoopAnimationsModule],
      providers: [
        { provide: ResolverService, useClass: MockResolverService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(LdapResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should expose controls via signal", () => {
    const controls = component.controls();
    expect(controls).toEqual(expect.objectContaining({
      LDAPURI: component.ldapUriControl,
      LDAPBASE: component.ldapBaseControl
    }));
  });

  it("should update controls when data input changes", () => {
    componentRef.setInput("data", {
      LDAPURI: "ldap://localhost",
      LDAPBASE: "dc=example,dc=com",
      LOGINNAMEATTRIBUTE: "uid",
      LDAPSEARCHFILTER: "(objectClass=*)",
      USERINFO: "description"
    });

    fixture.detectChanges();

    expect(component.ldapUriControl.value).toBe("ldap://localhost");
    expect(component.ldapBaseControl.value).toBe("dc=example,dc=com");
    expect(component.loginNameAttributeControl.value).toBe("uid");
    expect(component.ldapSearchFilterControl.value).toBe("(objectClass=*)");
    expect(component.userInfoControl.value).toBe("description");
  });

  it("should apply LDAP presets", () => {
    const preset = component.ldapPresets[0];
    component.applyLdapPreset(preset);
    expect(component.loginNameAttributeControl.value).toBe(preset.loginName);
    expect(component.ldapSearchFilterControl.value).toBe(preset.searchFilter);
    expect(component.userInfoControl.value).toBe(preset.userInfo);
    expect(component.uidTypeControl.value).toBe(preset.uidType);
    expect(component.multivalueAttributesControl.value).toBe("");
  });
});
