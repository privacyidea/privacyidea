import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScimResolverComponent } from './scim-resolver.component';

describe('ScimResolverComponent', () => {
  let component: ScimResolverComponent;
  let fixture: ComponentFixture<ScimResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScimResolverComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ScimResolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
