import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HttpResolverComponent } from './http-resolver.component';

describe('HttpResolverComponent', () => {
  let component: HttpResolverComponent;
  let fixture: ComponentFixture<HttpResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HttpResolverComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HttpResolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
