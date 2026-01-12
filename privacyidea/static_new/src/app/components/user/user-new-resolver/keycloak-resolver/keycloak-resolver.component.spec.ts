import { ComponentFixture, TestBed } from '@angular/core/testing';
import { KeycloakResolverComponent } from './keycloak-resolver.component';
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe('KeycloakResolverComponent', () => {
  let component: KeycloakResolverComponent;
  let componentRef: ComponentRef<KeycloakResolverComponent>;
  let fixture: ComponentFixture<KeycloakResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KeycloakResolverComponent, NoopAnimationsModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(KeycloakResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize default data on creation', () => {
    const data: any = {};
    componentRef.setInput('data', data);
    fixture.detectChanges();
    expect(data.base_url).toBe('http://localhost:8080');
    expect(data.config_authorization).toBeDefined();
  });
});
