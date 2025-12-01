import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LdapResolverComponent } from './ldap-resolver.component';

describe('LdapResolverComponent', () => {
  let component: LdapResolverComponent;
  let fixture: ComponentFixture<LdapResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LdapResolverComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LdapResolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
