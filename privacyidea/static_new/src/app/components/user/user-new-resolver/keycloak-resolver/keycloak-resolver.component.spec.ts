import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KeycloakResolverComponent } from './keycloak-resolver.component';

describe('KeycloakResolverComponent', () => {
  let component: KeycloakResolverComponent;
  let fixture: ComponentFixture<KeycloakResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KeycloakResolverComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(KeycloakResolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
