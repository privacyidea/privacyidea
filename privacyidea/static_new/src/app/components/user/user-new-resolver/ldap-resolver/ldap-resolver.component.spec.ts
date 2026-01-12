import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LdapResolverComponent } from './ldap-resolver.component';
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe('LdapResolverComponent', () => {
  let component: LdapResolverComponent;
  let componentRef: ComponentRef<LdapResolverComponent>;
  let fixture: ComponentFixture<LdapResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LdapResolverComponent, NoopAnimationsModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LdapResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit additionalFormFieldsChange on init', () => {
    const spy = jest.spyOn(component.additionalFormFieldsChange, 'emit');
    component.ngOnInit();
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({
      LDAPURI: component.ldapUriControl,
      LDAPBASE: component.ldapBaseControl
    }));
  });

  it('should update controls when data input changes', () => {
    componentRef.setInput('data', {
      LDAPURI: 'ldap://localhost',
      LDAPBASE: 'dc=example,dc=com',
      LOGINNAMEATTRIBUTE: 'uid',
      LDAPSEARCHFILTER: '(objectClass=*)',
      USERINFO: 'description'
    });

    fixture.detectChanges();

    expect(component.ldapUriControl.value).toBe('ldap://localhost');
    expect(component.ldapBaseControl.value).toBe('dc=example,dc=com');
    expect(component.loginNameAttributeControl.value).toBe('uid');
    expect(component.ldapSearchFilterControl.value).toBe('(objectClass=*)');
    expect(component.userInfoControl.value).toBe('description');
  });
});
